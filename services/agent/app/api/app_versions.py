"""Application Version Control（RFC-006 D-7 / M1 收尾）。

Snapshot 整個 application row 到 JSONB，可隨時 rollback。
版本號採自動遞增（per application）。Restore 時不刪除歷史版本，
而是先「快照當前」再覆寫，保留完整 audit trail。
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

# 哪些 application 欄位要納入 snapshot（排除 audit 欄與不可變欄）
_SNAPSHOT_COLS: tuple[str, ...] = (
    "name", "description", "icon", "type", "status",
    "llm_model_id", "system_prompt", "welcome_message",
    "suggested_questions", "knowledge_base_ids", "skill_ids",
    "config", "is_public", "folder_id",
)


class VersionCreate(BaseModel):
    note: str | None = Field(default=None, max_length=512)


class VersionOut(BaseModel):
    id:             uuid.UUID
    application_id: uuid.UUID
    version_number: int
    note:           str | None
    created_at:     datetime
    created_by:     uuid.UUID | None


async def _next_version_number(session: AsyncSession, app_id: uuid.UUID) -> int:
    row = await session.execute(
        text(
            "SELECT COALESCE(MAX(version_number), 0) AS n "
            "FROM application_versions WHERE application_id = :app_id"
        ),
        {"app_id": str(app_id)},
    )
    return int(dict(row.fetchone()._mapping)["n"]) + 1


async def _ensure_app_in_workspace(session: AsyncSession, app_id: uuid.UUID, ws):
    chk = await session.execute(
        text(
            "SELECT * FROM applications "
            "WHERE id = :id AND workspace_id = :ws AND status != 'deleted'"
        ),
        {"id": str(app_id), "ws": str(ws)},
    )
    r = chk.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Application 不存在")
    return r


async def _snapshot_app(session: AsyncSession, app_id: uuid.UUID, ws, note: str | None, by) -> dict:
    """把當前 application 寫成一筆 version。回傳 VersionOut 用 dict。"""
    row = await _ensure_app_in_workspace(session, app_id, ws)
    d = dict(row._mapping)
    snap = {col: d.get(col) for col in _SNAPSHOT_COLS}
    # JSONB 欄位 dict 已是 dict；uuid 轉 str
    for k, v in list(snap.items()):
        if isinstance(v, uuid.UUID):
            snap[k] = str(v)

    new_id = uuid.uuid4()
    ver = await _next_version_number(session, app_id)
    await session.execute(
        text(
            """
            INSERT INTO application_versions (
                id, application_id, workspace_id, version_number,
                snapshot, note, created_at, created_by
            ) VALUES (
                :id, :app_id, :ws, :ver, :snap::jsonb, :note, :now, :by
            )
            """
        ),
        {
            "id": str(new_id), "app_id": str(app_id), "ws": str(ws),
            "ver": ver, "snap": json.dumps(snap, ensure_ascii=False, default=str),
            "note": note, "now": datetime.utcnow(), "by": str(by) if by else None,
        },
    )
    return {
        "id": new_id, "application_id": app_id, "version_number": ver,
        "note": note, "created_at": datetime.utcnow(),
        "created_by": by,
    }


@router.post(
    "/{app_id}/versions",
    response_model=ApiResponse[VersionOut],
    status_code=status.HTTP_201_CREATED,
    summary="把當前 Application 設定快照成新版本",
)
async def create_version(
    app_id: uuid.UUID,
    body: VersionCreate,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    snap = await _snapshot_app(session, app_id, ctx.workspace_id, body.note, ctx.user_id)
    return ApiResponse(data=VersionOut(**snap))


@router.get(
    "/{app_id}/versions",
    response_model=ApiResponse[list[VersionOut]],
    summary="列出 Application 所有歷史版本",
)
async def list_versions(
    app_id: uuid.UUID,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    await _ensure_app_in_workspace(session, app_id, ctx.workspace_id)
    rows = await session.execute(
        text(
            "SELECT id, application_id, version_number, note, created_at, created_by "
            "FROM application_versions "
            "WHERE application_id = :app_id AND workspace_id = :ws "
            "ORDER BY version_number DESC"
        ),
        {"app_id": str(app_id), "ws": str(ctx.workspace_id)},
    )
    items = [VersionOut(**dict(r._mapping)) for r in rows.fetchall()]
    return ApiResponse(data=items)


@router.post(
    "/{app_id}/versions/{version_number}/restore",
    response_model=ApiResponse[VersionOut],
    summary="回滾到指定版本（同時把當前快照成新版本保留 audit）",
)
async def restore_version(
    app_id: uuid.UUID,
    version_number: int,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    # 1. 取目標版本 snapshot
    row = await session.execute(
        text(
            "SELECT snapshot FROM application_versions "
            "WHERE application_id = :app_id AND version_number = :ver "
            "AND workspace_id = :ws"
        ),
        {"app_id": str(app_id), "ver": version_number, "ws": str(ctx.workspace_id)},
    )
    r = row.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="版本不存在")
    target_snap = dict(r._mapping)["snapshot"]
    if isinstance(target_snap, str):
        target_snap = json.loads(target_snap)

    # 2. 先快照當前狀態（保留 audit trail）
    pre_snap = await _snapshot_app(
        session, app_id, ctx.workspace_id,
        note=f"自動快照（回滾至 v{version_number} 前）",
        by=ctx.user_id,
    )

    # 3. 用 target_snap 覆寫 applications row（JSONB 欄位 ::jsonb）
    JSONB_COLS = {"suggested_questions", "knowledge_base_ids", "skill_ids", "config"}
    set_parts: list[str] = ["updated_at = :now", "updated_by = :by"]
    params: dict = {
        "id": str(app_id), "ws": str(ctx.workspace_id),
        "now": datetime.utcnow(), "by": str(ctx.user_id),
    }
    for col, val in target_snap.items():
        if col in JSONB_COLS:
            set_parts.append(f"{col} = :{col}::jsonb")
            params[col] = json.dumps(val if val is not None else [], ensure_ascii=False)
        else:
            set_parts.append(f"{col} = :{col}")
            params[col] = val
    await session.execute(
        text(f"UPDATE applications SET {', '.join(set_parts)} WHERE id = :id AND workspace_id = :ws"),
        params,
    )

    return ApiResponse(data=VersionOut(**pre_snap), message=f"已回滾至 v{version_number}")
