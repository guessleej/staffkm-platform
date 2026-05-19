"""KB 資源授權 API（Round 10-4）。

預設規則（沒在 kb_grants 出現的 KB）：
- 沿用 workspace RBAC：require_member 可讀；editor 以上可寫
- 沒有 row → workspace 全體可讀

一旦某 KB 有 row → 切換到「白名單模式」：
- 只有授權對象（user / role / workspace 整體）能讀
- access=edit 才能改文件 / paragraph
- access=manage 才能改 grants 本身

API
- GET    /knowledge/bases/{kb_id}/grants
- POST   /knowledge/bases/{kb_id}/grants            { principal_type, principal_id, access }
- DELETE /knowledge/bases/{kb_id}/grants/{grant_id}
- GET    /knowledge/bases/{kb_id}/related-resources 哪些 application / chat 用到此 KB
"""
from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import KnowledgeBase
from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import (
    TenantContext, WorkspaceScopedQuery,
    require_admin, require_member,
)

router = APIRouter()


_VALID_PRINCIPAL_TYPES = ("user", "role", "workspace")
_VALID_ROLES = ("owner", "admin", "editor", "viewer")
_VALID_ACCESS = ("read", "edit", "manage")


class GrantCreate(BaseModel):
    principal_type: Literal["user", "role", "workspace"]
    principal_id:   str = Field(..., min_length=1, max_length=128)
    access:         Literal["read", "edit", "manage"] = "read"


async def _verify_kb(kb_id: uuid.UUID, ctx: TenantContext, session: AsyncSession) -> KnowledgeBase:
    q = WorkspaceScopedQuery(KnowledgeBase).select().where(KnowledgeBase.id == kb_id)
    kb = (await session.execute(q)).scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="知識庫不存在或不屬於此工作區")
    return kb


@router.get("/{kb_id}/grants", response_model=ApiResponse)
async def list_grants(
    kb_id: uuid.UUID,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    await _verify_kb(kb_id, ctx, session)
    rows = await session.execute(
        text(
            "SELECT id, principal_type, principal_id, access, created_at "
            "FROM kb_grants WHERE kb_id = :id AND workspace_id = :ws "
            "ORDER BY principal_type, principal_id"
        ),
        {"id": str(kb_id), "ws": str(ctx.workspace_id)},
    )
    return ApiResponse(data=[dict(r._mapping) for r in rows.fetchall()])


@router.post("/{kb_id}/grants", response_model=ApiResponse)
async def add_grant(
    kb_id: uuid.UUID,
    body: GrantCreate,
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """新增授權；admin / owner 才能改 ACL（避免自己解鎖自己）。"""
    await _verify_kb(kb_id, ctx, session)
    if body.principal_type == "role" and body.principal_id not in _VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"role 必須為 {_VALID_ROLES}")

    gid = str(uuid.uuid4())
    try:
        await session.execute(
            text(
                "INSERT INTO kb_grants "
                "(id, workspace_id, kb_id, principal_type, principal_id, access, created_by) "
                "VALUES (:id, :ws, :kb, :pt, :pi, :ac, :by) "
                "ON CONFLICT (kb_id, principal_type, principal_id) DO UPDATE "
                "  SET access = EXCLUDED.access"
            ),
            {
                "id": gid, "ws": str(ctx.workspace_id), "kb": str(kb_id),
                "pt": body.principal_type, "pi": body.principal_id, "ac": body.access,
                "by": str(ctx.user_id) if ctx.user_id else None,
            },
        )
        await session.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"授權新增失敗：{e}") from e
    return ApiResponse(data={"id": gid}, message="授權已新增")


@router.delete("/{kb_id}/grants/{grant_id}", response_model=ApiResponse)
async def delete_grant(
    kb_id: uuid.UUID,
    grant_id: uuid.UUID,
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    await _verify_kb(kb_id, ctx, session)
    res = await session.execute(
        text("DELETE FROM kb_grants WHERE id = :gid AND kb_id = :kb AND workspace_id = :ws"),
        {"gid": str(grant_id), "kb": str(kb_id), "ws": str(ctx.workspace_id)},
    )
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="授權項目不存在")
    return ApiResponse(message="授權已刪除")


# ── 關聯資源（查哪些 application 引用此 KB）─────────────────────────
@router.get("/{kb_id}/related-resources", response_model=ApiResponse)
async def list_related_resources(
    kb_id: uuid.UUID,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    """跨服務查詢：哪些 application.knowledge_base_ids 含此 kb_id。

    走原生 SQL 避開跨 service ORM 依賴（applications 在 agent service）。
    """
    await _verify_kb(kb_id, ctx, session)
    apps_rows = await session.execute(
        text(
            "SELECT id, name, type, status, updated_at "
            "FROM applications "
            "WHERE workspace_id = :ws "
            "  AND status != 'deleted' "
            "  AND knowledge_base_ids @> CAST(:kb_arr AS jsonb) "
            "ORDER BY updated_at DESC NULLS LAST"
        ),
        {
            "ws":     str(ctx.workspace_id),
            "kb_arr": f'["{kb_id}"]',
        },
    )
    apps: list[dict] = []
    try:
        apps = [dict(r._mapping) for r in apps_rows.fetchall()]
    except Exception:
        # applications 表不在或欄位不同 → 安靜跳過
        apps = []
    return ApiResponse(data={"applications": apps})
