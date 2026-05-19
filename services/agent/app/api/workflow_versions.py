"""Workflow Version Control（RFC-008 / M2 scaffold）。

Snapshot 整個 workflow（nodes + edges）到 JSONB，可隨時 rollback。
版本號 per application 自動遞增。restore 同 D-7 模式：先快照當前再覆寫。
"""
import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_member, require_writer

router = APIRouter()


class WfVersionCreate(BaseModel):
    note: str | None = Field(default=None, max_length=512)


class WfVersionOut(BaseModel):
    id:             uuid.UUID
    application_id: uuid.UUID
    version_number: int
    note:           str | None
    created_at:     datetime
    created_by:     uuid.UUID | None


async def _next_ver(session: AsyncSession, app_id: uuid.UUID) -> int:
    row = await session.execute(
        text(
            "SELECT COALESCE(MAX(version_number), 0) AS n "
            "FROM workflow_versions WHERE application_id = :app_id"
        ),
        {"app_id": str(app_id)},
    )
    return int(dict(row.fetchone()._mapping)["n"]) + 1


async def _snapshot_workflow(
    session: AsyncSession, app_id: uuid.UUID, ws, note: str | None, by
) -> dict:
    # 取當前 nodes + edges
    n_rows = await session.execute(
        text(
            "SELECT id, node_type, node_key, label, config, position "
            "FROM workflow_nodes WHERE application_id = :id AND workspace_id = :ws"
        ),
        {"id": str(app_id), "ws": str(ws)},
    )
    e_rows = await session.execute(
        text(
            "SELECT id, source_node_key, target_node_key, condition "
            "FROM workflow_edges WHERE application_id = :id AND workspace_id = :ws"
        ),
        {"id": str(app_id), "ws": str(ws)},
    )
    nodes = [dict(r._mapping) for r in n_rows.fetchall()]
    edges = [dict(r._mapping) for r in e_rows.fetchall()]

    # uuid → str for JSON serialization
    def _norm(rows):
        for r in rows:
            for k, v in list(r.items()):
                if isinstance(v, uuid.UUID): r[k] = str(v)
        return rows
    nodes, edges = _norm(nodes), _norm(edges)

    new_id = uuid.uuid4()
    ver = await _next_ver(session, app_id)
    await session.execute(
        text(
            """
            INSERT INTO workflow_versions (
                id, application_id, workspace_id, version_number,
                nodes, edges, note, created_at, created_by
            ) VALUES (
                :id, :app_id, :ws, :ver, CAST(:nodes AS jsonb), CAST(:edges AS jsonb),
                :note, :now, :by
            )
            """
        ),
        {
            "id": str(new_id), "app_id": str(app_id), "ws": str(ws),
            "ver": ver,
            "nodes": json.dumps(nodes, ensure_ascii=False, default=str),
            "edges": json.dumps(edges, ensure_ascii=False, default=str),
            "note": note,
            "now": datetime.utcnow(),
            "by": str(by) if by else None,
        },
    )
    return {
        "id": new_id, "application_id": app_id, "version_number": ver,
        "note": note, "created_at": datetime.utcnow(), "created_by": by,
    }


@router.post(
    "/{app_id}/workflow/versions",
    response_model=ApiResponse[WfVersionOut],
    status_code=status.HTTP_201_CREATED,
    summary="把當前 workflow 快照成新版本",
)
async def create_wf_version(
    app_id: uuid.UUID,
    body: WfVersionCreate,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    snap = await _snapshot_workflow(session, app_id, ctx.workspace_id, body.note, ctx.user_id)
    return ApiResponse(data=WfVersionOut(**snap))


@router.get(
    "/{app_id}/workflow/versions",
    response_model=ApiResponse[list[WfVersionOut]],
    summary="列出 workflow 版本歷史",
)
async def list_wf_versions(
    app_id: uuid.UUID,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    rows = await session.execute(
        text(
            "SELECT id, application_id, version_number, note, created_at, created_by "
            "FROM workflow_versions "
            "WHERE application_id = :app_id AND workspace_id = :ws "
            "ORDER BY version_number DESC"
        ),
        {"app_id": str(app_id), "ws": str(ctx.workspace_id)},
    )
    return ApiResponse(data=[WfVersionOut(**dict(r._mapping)) for r in rows.fetchall()])


@router.post(
    "/{app_id}/workflow/versions/{version_number}/restore",
    response_model=ApiResponse[WfVersionOut],
    summary="回滾 workflow 到指定版本（先快照當前保留 audit）",
)
async def restore_wf_version(
    app_id: uuid.UUID,
    version_number: int,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    row = await session.execute(
        text(
            "SELECT nodes, edges FROM workflow_versions "
            "WHERE application_id = :app_id AND version_number = :ver AND workspace_id = :ws"
        ),
        {"app_id": str(app_id), "ver": version_number, "ws": str(ctx.workspace_id)},
    )
    r = row.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="版本不存在")
    d = dict(r._mapping)
    target_nodes = d["nodes"] if isinstance(d["nodes"], list) else json.loads(d["nodes"])
    target_edges = d["edges"] if isinstance(d["edges"], list) else json.loads(d["edges"])

    # 先快照當前
    pre_snap = await _snapshot_workflow(
        session, app_id, ctx.workspace_id,
        note=f"自動快照（回滾 workflow 至 v{version_number} 前）",
        by=ctx.user_id,
    )

    # 清除當前 nodes / edges 再依 snapshot 寫回
    await session.execute(
        text("DELETE FROM workflow_edges WHERE application_id = :id AND workspace_id = :ws"),
        {"id": str(app_id), "ws": str(ctx.workspace_id)},
    )
    await session.execute(
        text("DELETE FROM workflow_nodes WHERE application_id = :id AND workspace_id = :ws"),
        {"id": str(app_id), "ws": str(ctx.workspace_id)},
    )

    for n in target_nodes:
        await session.execute(
            text(
                """
                INSERT INTO workflow_nodes (
                    id, application_id, workspace_id, node_type, node_key,
                    label, config, position
                ) VALUES (
                    :id, :app, :ws, :type, :key, :label, CAST(:config AS jsonb), CAST(:pos AS jsonb)
                )
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "app": str(app_id), "ws": str(ctx.workspace_id),
                "type": n.get("node_type"), "key": n.get("node_key"),
                "label": n.get("label") or "",
                "config": json.dumps(n.get("config") or {}, ensure_ascii=False),
                "pos": json.dumps(n.get("position") or {"x": 0, "y": 0}, ensure_ascii=False),
            },
        )
    for e in target_edges:
        cond = e.get("condition")
        await session.execute(
            text(
                """
                INSERT INTO workflow_edges (
                    id, application_id, workspace_id, source_node_key,
                    target_node_key, condition
                ) VALUES (
                    :id, :app, :ws, :src, :tgt, CAST(:cond AS jsonb)
                )
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "app": str(app_id), "ws": str(ctx.workspace_id),
                "src": e.get("source_node_key"), "tgt": e.get("target_node_key"),
                "cond": json.dumps(cond, ensure_ascii=False) if cond is not None else None,
            },
        )
    return ApiResponse(data=WfVersionOut(**pre_snap), message=f"已回滾 workflow 至 v{version_number}")
