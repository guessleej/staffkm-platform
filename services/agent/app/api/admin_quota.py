"""Admin 跨 workspace quota / usage 管理（v3.2 P3）。

非 workspace-scoped — admin role 可列所有 workspace + 設任一 ws 的 cap。
這裡用 X-User-Roles (gateway 注入) 直接判斷，而不是 tenant context，
因為 endpoint 不在 /workspace/{ws}/ 之下，middleware 不會建 TenantContext。
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session

router = APIRouter()


def require_admin_role(request: Request) -> str | None:
    """非 workspace-scoped 場景下用 role header 判斷。回傳 user_id（若可解析）。"""
    roles = getattr(request.state, "roles", []) or []
    if "admin" not in roles:
        raise HTTPException(status_code=403, detail="需要管理員權限")
    return getattr(request.state, "user_id", None)


class QuotaUpdateBody(BaseModel):
    monthly_token_cap:    int | None   = None
    monthly_cost_cap_usd: float | None = None


@router.get("/quotas", response_model=ApiResponse, summary="列出所有 workspace 的 quota + 當月用量")
async def list_workspace_quotas(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    require_admin_role(request)
    rows = await session.execute(text("""
        SELECT
            w.id              AS workspace_id,
            w.name            AS workspace_name,
            q.monthly_token_cap,
            q.monthly_cost_cap_usd,
            COALESCE((
                SELECT SUM(total_tokens)
                FROM model_usage_logs m
                WHERE m.workspace_id = w.id
                  AND m.created_at >= date_trunc('month', now())
            ), 0)::BIGINT     AS tokens_used,
            COALESCE((
                SELECT SUM(cost_usd)
                FROM model_usage_logs m
                WHERE m.workspace_id = w.id
                  AND m.created_at >= date_trunc('month', now())
            ), 0)::NUMERIC(12,6) AS cost_used
        FROM workspace w
        LEFT JOIN workspace_quotas q ON q.workspace_id = w.id
        ORDER BY w.name
    """))
    items = [dict(r._mapping) for r in rows.fetchall()]
    for it in items:
        if it.get("cost_used") is not None:
            it["cost_used"] = float(it["cost_used"])
        if it.get("monthly_cost_cap_usd") is not None:
            it["monthly_cost_cap_usd"] = float(it["monthly_cost_cap_usd"])
        if it.get("workspace_id") is not None:
            it["workspace_id"] = str(it["workspace_id"])
    return ApiResponse(data={"items": items, "month": datetime.utcnow().strftime("%Y-%m")})


@router.put("/quotas/{workspace_id}", response_model=ApiResponse, summary="設定指定 workspace 的 quota")
async def set_workspace_quota(
    request: Request,
    body: QuotaUpdateBody,
    workspace_id: uuid.UUID = Path(...),
    session: AsyncSession = Depends(get_session),
):
    actor_user_id = require_admin_role(request)
    await session.execute(text("""
        INSERT INTO workspace_quotas (
            workspace_id, monthly_token_cap, monthly_cost_cap_usd, updated_at, updated_by
        ) VALUES (:ws, :tok, :cost, now(), :by)
        ON CONFLICT (workspace_id) DO UPDATE
          SET monthly_token_cap    = EXCLUDED.monthly_token_cap,
              monthly_cost_cap_usd = EXCLUDED.monthly_cost_cap_usd,
              updated_at           = now(),
              updated_by           = EXCLUDED.updated_by
    """), {
        "ws":   str(workspace_id),
        "tok":  body.monthly_token_cap,
        "cost": body.monthly_cost_cap_usd,
        "by":   actor_user_id,
    })
    return ApiResponse(message="quota 已更新")
