"""User-level quota API（v3.3 D1）。

workspace-scoped；admin 才能改。注意：workspace_member 是單數 table 名
（packages/python/staffkm-tenant/staffkm_tenant/models.py:67）。
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_admin

router = APIRouter()


class UserQuotaBody(BaseModel):
    monthly_token_cap:    int | None   = None
    monthly_cost_cap_usd: float | None = None


@router.get("", response_model=ApiResponse, summary="列出 workspace 內所有 user 用量 + cap")
async def list_user_quotas(
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    rows = await session.execute(text("""
        SELECT u.id AS user_id, u.username, u.email,
               q.monthly_token_cap, q.monthly_cost_cap_usd,
               COALESCE((
                 SELECT SUM(total_tokens) FROM model_usage_logs m
                 WHERE m.workspace_id = :ws AND m.user_id = u.id
                   AND m.created_at >= date_trunc('month', now())
               ), 0)::BIGINT AS tokens_used,
               COALESCE((
                 SELECT SUM(cost_usd) FROM model_usage_logs m
                 WHERE m.workspace_id = :ws AND m.user_id = u.id
                   AND m.created_at >= date_trunc('month', now())
               ), 0)::NUMERIC(12,6) AS cost_used
        FROM users u
        JOIN workspace_member wm ON wm.user_id = u.id AND wm.workspace_id = :ws
        LEFT JOIN user_quotas q ON q.user_id = u.id AND q.workspace_id = :ws
        WHERE wm.is_active = TRUE
        ORDER BY tokens_used DESC
    """), {"ws": str(ctx.workspace_id)})
    items = [dict(r._mapping) for r in rows.fetchall()]
    for it in items:
        if it.get("user_id") is not None:
            it["user_id"] = str(it["user_id"])
        for k in ("cost_used", "monthly_cost_cap_usd"):
            if it.get(k) is not None:
                it[k] = float(it[k])
    return ApiResponse(data={"items": items})


@router.put("/{user_id}", response_model=ApiResponse, summary="設定某 user 的 quota")
async def set_user_quota(
    body: UserQuotaBody,
    user_id: uuid.UUID = Path(...),
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(text("""
        INSERT INTO user_quotas (workspace_id, user_id, monthly_token_cap, monthly_cost_cap_usd, updated_at, updated_by)
        VALUES (:ws, :uid, :tok, :cost, now(), :by)
        ON CONFLICT (workspace_id, user_id) DO UPDATE
        SET monthly_token_cap = EXCLUDED.monthly_token_cap,
            monthly_cost_cap_usd = EXCLUDED.monthly_cost_cap_usd,
            updated_at = now(), updated_by = EXCLUDED.updated_by
    """), {
        "ws": str(ctx.workspace_id), "uid": str(user_id),
        "tok": body.monthly_token_cap, "cost": body.monthly_cost_cap_usd,
        "by": str(ctx.user_id) if ctx.user_id else None,
    })
    await session.commit()
    return ApiResponse(message="user quota updated")
