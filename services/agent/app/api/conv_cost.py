"""Conversation cost API (v3.7 P1).

GET /workspace/{ws}/conversations/{conv_id}/cost — 本對話總 cost + 按 message_id 細分
"""
from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_member

router = APIRouter()


@router.get("/{conversation_id}/cost", response_model=ApiResponse, summary="本對話總 cost + 按 message_id 細分")
async def conversation_cost(
    conversation_id: uuid.UUID = Path(...),
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    # total
    r = await session.execute(text("""
        SELECT
            COALESCE(SUM(total_tokens), 0)::BIGINT AS tokens,
            COALESCE(SUM(cost_usd),    0)::NUMERIC(12,6) AS cost,
            COUNT(*)::INT AS calls
        FROM model_usage_logs
        WHERE workspace_id = :ws AND conversation_id = :cid
    """), {"ws": str(ctx.workspace_id), "cid": str(conversation_id)})
    total_row = r.fetchone()
    total = dict(total_row._mapping) if total_row else {"tokens": 0, "cost": 0, "calls": 0}
    if total.get("cost") is not None:
        total["cost"] = float(total["cost"])

    # by message
    r2 = await session.execute(text("""
        SELECT
            message_id,
            COALESCE(SUM(total_tokens), 0)::BIGINT AS tokens,
            COALESCE(SUM(cost_usd),    0)::NUMERIC(12,6) AS cost,
            COUNT(*)::INT AS calls,
            MIN(created_at) AS started_at
        FROM model_usage_logs
        WHERE workspace_id = :ws AND conversation_id = :cid
        GROUP BY message_id
        ORDER BY started_at ASC
    """), {"ws": str(ctx.workspace_id), "cid": str(conversation_id)})
    by_message = []
    for r in r2.fetchall():
        d = dict(r._mapping)
        if d.get("cost") is not None:
            d["cost"] = float(d["cost"])
        by_message.append(d)

    return ApiResponse(data={
        "conversation_id": str(conversation_id),
        "total": total,
        "by_message": by_message,
    })
