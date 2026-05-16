"""Token 計帳 + Quota API（M3 中段-D）。

- GET /usage/summary       — 當月 tokens / cost / requests + quota 設定
- GET /usage/logs          — 分頁列出 usage logs（時間倒序）
- GET /quota               — 取得當前 workspace quota
- PUT /quota               — 設定 quota（admin / owner）
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.usage import get_monthly_usage, get_quota
from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_admin, require_member

router = APIRouter()


class QuotaUpdate(BaseModel):
    monthly_token_cap:    int | None   = None
    monthly_cost_cap_usd: float | None = None


@router.get("/summary", response_model=ApiResponse, summary="當月用量總覽")
async def usage_summary(
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    usage = await get_monthly_usage(session, str(ctx.workspace_id))
    quota = await get_quota(session, str(ctx.workspace_id))
    return ApiResponse(data={
        "month":   datetime.utcnow().strftime("%Y-%m"),
        "usage":   usage,
        "quota":   quota,
    })


@router.get("/logs", response_model=ApiResponse, summary="分頁列出 usage logs")
async def usage_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    offset = (page - 1) * page_size
    rows = await session.execute(
        text(
            """
            SELECT id, user_id, application_id, provider_type, model,
                   prompt_tokens, completion_tokens, total_tokens,
                   cost_usd, latency_ms, status, error, created_at
            FROM model_usage_logs
            WHERE workspace_id = :ws
            ORDER BY created_at DESC
            LIMIT :lim OFFSET :off
            """
        ),
        {"ws": str(ctx.workspace_id), "lim": page_size, "off": offset},
    )
    items: list[dict[str, Any]] = [dict(r._mapping) for r in rows.fetchall()]
    return ApiResponse(data={"items": items, "page": page, "page_size": page_size})


@router.get("/quota", response_model=ApiResponse, summary="取得 workspace quota")
async def quota_get(
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    return ApiResponse(data=await get_quota(session, str(ctx.workspace_id)))


@router.put("/quota", response_model=ApiResponse, summary="更新 workspace quota（admin / owner）")
async def quota_update(
    body: QuotaUpdate,
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(
        text(
            """
            INSERT INTO workspace_quotas (
                workspace_id, monthly_token_cap, monthly_cost_cap_usd,
                updated_at, updated_by
            )
            VALUES (:ws, :tok, :cost, now(), :by)
            ON CONFLICT (workspace_id) DO UPDATE
              SET monthly_token_cap    = EXCLUDED.monthly_token_cap,
                  monthly_cost_cap_usd = EXCLUDED.monthly_cost_cap_usd,
                  updated_at           = now(),
                  updated_by           = EXCLUDED.updated_by
            """
        ),
        {
            "ws":   str(ctx.workspace_id),
            "tok":  body.monthly_token_cap,
            "cost": body.monthly_cost_cap_usd,
            "by":   str(ctx.user_id) if ctx.user_id else None,
        },
    )
    return ApiResponse(data=await get_quota(session, str(ctx.workspace_id)), message="quota 已更新")
