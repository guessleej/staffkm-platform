"""Workflow API — 管理 application 的 workflow 節點與執行（workspace-scoped）。

權限模型：
  GET   /workflow         require_member  （任何成員可看）
  POST  /workflow         require_writer  （editor 以上可改）
  POST  /workflow/chat    require_member  （任何成員可執行）
"""
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.workflow.executor import WorkflowExecutor
from app.core.usage import QuotaExceeded
from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_member, require_writer

router = APIRouter()


# ── Pydantic Schemas ────────────────────────────────────────────────────────


class WorkflowNode(BaseModel):
    id: str = ""
    node_key: str = ""
    node_type: str
    label: str = ""
    config: dict[str, Any] = {}
    position: dict[str, float] = {"x": 0, "y": 0}


class WorkflowEdge(BaseModel):
    id: str = ""
    source_node_key: str
    target_node_key: str
    condition: Any = None


class WorkflowSave(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class WorkflowChatRequest(BaseModel):
    user_input: str
    session_id: str = ""
    conversation_id: str | None = None  # v3.8 P1: optional, for cost attribution


async def _ensure_app_in_workspace(
    session: AsyncSession, app_id: uuid.UUID, workspace_id
) -> None:
    """檢查 application 是否存在且屬於當前 workspace；否則 404。"""
    check = await session.execute(
        text(
            "SELECT id FROM applications "
            "WHERE id = :id AND workspace_id = :ws AND status != 'deleted'"
        ),
        {"id": str(app_id), "ws": str(workspace_id)},
    )
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="應用程式不存在")


# ── 取得工作流程 ────────────────────────────────────────────────────────────


@router.get(
    "/{app_id}/workflow",
    response_model=ApiResponse,
    summary="取得 Application 的工作流程",
)
async def get_workflow(
    app_id: uuid.UUID,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    await _ensure_app_in_workspace(session, app_id, ctx.workspace_id)

    nodes_rows = await session.execute(
        text(
            "SELECT * FROM workflow_nodes "
            "WHERE application_id = :app_id AND workspace_id = :ws "
            "ORDER BY created_at"
        ),
        {"app_id": str(app_id), "ws": str(ctx.workspace_id)},
    )
    edges_rows = await session.execute(
        text(
            "SELECT * FROM workflow_edges "
            "WHERE application_id = :app_id AND workspace_id = :ws"
        ),
        {"app_id": str(app_id), "ws": str(ctx.workspace_id)},
    )
    nodes = [dict(r._mapping) for r in nodes_rows.fetchall()]
    edges = [dict(r._mapping) for r in edges_rows.fetchall()]

    for n in nodes:
        if isinstance(n.get("config"), str):
            n["config"] = json.loads(n["config"])
        pos = n.get("position") or {"x": 0, "y": 0}
        if isinstance(pos, str):
            pos = json.loads(pos)
        n["position"] = pos

    for e in edges:
        cond = e.get("condition")
        if isinstance(cond, str):
            try:
                e["condition"] = json.loads(cond)
            except Exception:
                pass

    return ApiResponse(data={"nodes": nodes, "edges": edges})


# ── 儲存工作流程 ────────────────────────────────────────────────────────────


@router.post(
    "/{app_id}/workflow",
    response_model=ApiResponse,
    summary="儲存工作流程（覆寫，editor 以上）",
)
async def save_workflow(
    app_id: uuid.UUID,
    body: WorkflowSave,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    await _ensure_app_in_workspace(session, app_id, ctx.workspace_id)

    # 清除舊的工作流程（限定 workspace 內）
    await session.execute(
        text(
            "DELETE FROM workflow_edges "
            "WHERE application_id = :app_id AND workspace_id = :ws"
        ),
        {"app_id": str(app_id), "ws": str(ctx.workspace_id)},
    )
    await session.execute(
        text(
            "DELETE FROM workflow_nodes "
            "WHERE application_id = :app_id AND workspace_id = :ws"
        ),
        {"app_id": str(app_id), "ws": str(ctx.workspace_id)},
    )

    # 插入節點（同時寫 workspace_id）
    for node in body.nodes:
        node_id = node.get("id") or str(uuid.uuid4())
        node_key = node.get("node_key") or node_id
        position = node.get("position") or {"x": 0, "y": 0}
        if isinstance(position, str):
            position = json.loads(position)
        await session.execute(
            text("""
                INSERT INTO workflow_nodes (
                    id, application_id, workspace_id, node_type, node_key,
                    label, config, position
                )
                VALUES (
                    :id, :app_id, :ws, :node_type, :node_key,
                    :label, CAST(:config AS jsonb), CAST(:position AS jsonb)
                )
            """),
            {
                "id": node_id,
                "app_id": str(app_id),
                "ws": str(ctx.workspace_id),
                "node_type": node.get("node_type", "start"),
                "node_key": node_key,
                "label": node.get("label", ""),
                "config": json.dumps(node.get("config", {}), ensure_ascii=False),
                "position": json.dumps(position, ensure_ascii=False),
            },
        )

    # 插入邊（同時寫 workspace_id）
    for edge in body.edges:
        edge_id = edge.get("id") or str(uuid.uuid4())
        condition = edge.get("condition")
        condition_json = (
            json.dumps(condition, ensure_ascii=False) if condition is not None else None
        )
        await session.execute(
            text("""
                INSERT INTO workflow_edges (
                    id, application_id, workspace_id, source_node_key,
                    target_node_key, condition
                )
                VALUES (
                    :id, :app_id, :ws, :source, :target, CAST(:condition AS jsonb)
                )
            """),
            {
                "id": edge_id,
                "app_id": str(app_id),
                "ws": str(ctx.workspace_id),
                "source": edge["source_node_key"],
                "target": edge["target_node_key"],
                "condition": condition_json,
            },
        )

    return ApiResponse(message="工作流程已儲存")


# ── 執行工作流程（SSE） ─────────────────────────────────────────────────────


@router.post(
    "/{app_id}/workflow/chat",
    summary="執行工作流程（SSE 串流）",
)
async def run_workflow(
    app_id: uuid.UUID,
    body: WorkflowChatRequest,
    request: Request,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    await _ensure_app_in_workspace(session, app_id, ctx.workspace_id)

    nodes_rows = await session.execute(
        text(
            "SELECT * FROM workflow_nodes "
            "WHERE application_id = :app_id AND workspace_id = :ws "
            "ORDER BY created_at"
        ),
        {"app_id": str(app_id), "ws": str(ctx.workspace_id)},
    )
    edges_rows = await session.execute(
        text(
            "SELECT * FROM workflow_edges "
            "WHERE application_id = :app_id AND workspace_id = :ws"
        ),
        {"app_id": str(app_id), "ws": str(ctx.workspace_id)},
    )
    nodes = [dict(r._mapping) for r in nodes_rows.fetchall()]
    edges = [dict(r._mapping) for r in edges_rows.fetchall()]

    if not nodes:
        raise HTTPException(status_code=400, detail="工作流程尚未設定，請先建立節點")

    for n in nodes:
        if isinstance(n.get("config"), str):
            n["config"] = json.loads(n["config"])

    # M2-2：讀 application.workflow_manager 決定執行策略
    mgr_row = await session.execute(
        text("SELECT workflow_manager FROM applications WHERE id = :id"),
        {"id": str(app_id)},
    )
    mgr_value = mgr_row.fetchone()
    workflow_manager = (
        dict(mgr_value._mapping).get("workflow_manager") if mgr_value else None
    ) or "simple"

    # 多租戶上下文：一路傳到所有 _exec_* node
    executor = WorkflowExecutor(
        nodes=nodes,
        edges=edges,
        workspace_id=str(ctx.workspace_id),
        user_id=str(ctx.user_id),
        roles=[ctx.role.value],
        workflow_manager=workflow_manager,
        application_id=str(app_id),  # v3.3：metering 歸帳到 application
        conversation_id=body.conversation_id,  # v3.8 P1: 對話歸因（trigger 走 None）
    )

    async def event_generator():
        try:
            async for event in executor.execute(
                user_input=body.user_input,
                user_id=str(ctx.user_id),
            ):
                yield event
        except QuotaExceeded as qe:
            # v3.3：quota 超額；SSE 已開，回 error event 而非 429
            yield {"event": "error", "data": f"quota_exceeded: {qe}"}

    return EventSourceResponse(event_generator())
