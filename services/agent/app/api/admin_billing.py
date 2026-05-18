"""Admin billing API (v3.8 P2) — 跨 workspace per-user 用量報表。

admin 角色限定（讀 X-User-Roles header，跟既有 admin_quotas / heartbeats / webhook_outbox 同 pattern）。
"""
from __future__ import annotations
import csv
import io
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Path, Query, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_read_session  # v4.0 P6: 報表全走 read replica

router = APIRouter()


def _require_admin(request: Request) -> None:
    roles = getattr(request.state, "roles", []) or []
    if "admin" not in roles:
        raise HTTPException(status_code=403, detail="admin only")


@router.get("/users", response_model=ApiResponse, summary="當月所有 user billing 總覽")
async def list_user_billing(
    request: Request,
    month: str | None = Query(default=None, description="YYYY-MM；預設當月"),
    session: AsyncSession = Depends(get_read_session),  # v4.0 P6: read replica
):
    _require_admin(request)

    # parse month
    if month:
        try:
            start = datetime.strptime(month + "-01", "%Y-%m-%d")
        except ValueError:
            raise HTTPException(400, "invalid month format, use YYYY-MM")
    else:
        now = datetime.utcnow()
        start = datetime(now.year, now.month, 1)

    rows = await session.execute(text("""
        SELECT u.id            AS user_id,
               u.username,
               u.email,
               w.name          AS workspace_name,
               m.workspace_id,
               COUNT(*)::INT   AS calls,
               SUM(m.total_tokens)::BIGINT AS tokens,
               SUM(m.cost_usd)::float      AS cost,
               COUNT(DISTINCT m.conversation_id)::INT AS conversations
        FROM model_usage_logs m
        JOIN users u ON u.id = m.user_id
        LEFT JOIN workspaces w ON w.id = m.workspace_id
        WHERE m.created_at >= :start
          AND m.created_at < :start + INTERVAL '1 month'
          AND m.user_id IS NOT NULL
        GROUP BY u.id, u.username, u.email, w.name, m.workspace_id
        ORDER BY cost DESC NULLS LAST
        LIMIT 500
    """), {"start": start})

    items = []
    total_cost = 0.0
    total_tokens = 0
    for r in rows.fetchall():
        d = dict(r._mapping)
        c = float(d.get("cost") or 0)
        total_cost += c
        total_tokens += int(d.get("tokens") or 0)
        items.append(d)

    return ApiResponse(data={
        "month": start.strftime("%Y-%m"),
        "items": items,
        "summary": {
            "total_cost":   total_cost,
            "total_tokens": total_tokens,
            "user_count":   len(items),
        },
    })


@router.get("/users/{user_id}", response_model=ApiResponse, summary="單一 user 詳情（top conv / by feature / daily）")
async def user_billing_detail(
    request: Request,
    user_id: uuid.UUID = Path(...),
    month: str | None = Query(default=None),
    session: AsyncSession = Depends(get_read_session),  # v4.0 P6: read replica
):
    _require_admin(request)

    if month:
        try:
            start = datetime.strptime(month + "-01", "%Y-%m-%d")
        except ValueError:
            raise HTTPException(400, "invalid month")
    else:
        now = datetime.utcnow()
        start = datetime(now.year, now.month, 1)

    params = {"uid": str(user_id), "start": start}

    # by feature
    fr = await session.execute(text("""
        SELECT COALESCE(feature, 'unknown') AS feature,
               COUNT(*)::INT AS calls,
               SUM(total_tokens)::BIGINT AS tokens,
               SUM(cost_usd)::float AS cost
        FROM model_usage_logs
        WHERE user_id = :uid AND created_at >= :start
          AND created_at < :start + INTERVAL '1 month'
        GROUP BY feature ORDER BY cost DESC NULLS LAST
    """), params)
    by_feature = [dict(r._mapping) for r in fr.fetchall()]

    # top conversations
    cr = await session.execute(text("""
        SELECT conversation_id,
               COUNT(*)::INT AS calls,
               SUM(total_tokens)::BIGINT AS tokens,
               SUM(cost_usd)::float AS cost,
               MIN(created_at) AS started_at
        FROM model_usage_logs
        WHERE user_id = :uid AND created_at >= :start
          AND created_at < :start + INTERVAL '1 month'
          AND conversation_id IS NOT NULL
        GROUP BY conversation_id ORDER BY cost DESC NULLS LAST LIMIT 20
    """), params)
    top_convs = [dict(r._mapping) for r in cr.fetchall()]

    # daily timeseries
    dr = await session.execute(text("""
        SELECT date_trunc('day', created_at)::date AS day,
               COUNT(*)::INT AS calls,
               SUM(total_tokens)::BIGINT AS tokens,
               SUM(cost_usd)::float AS cost
        FROM model_usage_logs
        WHERE user_id = :uid AND created_at >= :start
          AND created_at < :start + INTERVAL '1 month'
        GROUP BY 1 ORDER BY 1
    """), params)
    daily = [{
        "day": str(r.day), "calls": int(r.calls), "tokens": int(r.tokens or 0),
        "cost": float(r.cost or 0),
    } for r in dr.fetchall()]

    return ApiResponse(data={
        "month": start.strftime("%Y-%m"),
        "by_feature": by_feature,
        "top_conversations": top_convs,
        "daily": daily,
    })


@router.get("/users.csv", summary="匯出當月所有 user billing CSV")
async def export_csv(
    request: Request,
    month: str | None = Query(default=None),
    session: AsyncSession = Depends(get_read_session),  # v4.0 P6: read replica
):
    _require_admin(request)

    if month:
        try:
            start = datetime.strptime(month + "-01", "%Y-%m-%d")
        except ValueError:
            raise HTTPException(400, "invalid month")
    else:
        now = datetime.utcnow()
        start = datetime(now.year, now.month, 1)

    rows = await session.execute(text("""
        SELECT u.username, u.email, w.name AS workspace,
               COUNT(*)::INT AS calls,
               SUM(m.total_tokens) AS tokens,
               SUM(m.cost_usd) AS cost
        FROM model_usage_logs m
        JOIN users u ON u.id = m.user_id
        LEFT JOIN workspaces w ON w.id = m.workspace_id
        WHERE m.created_at >= :start
          AND m.created_at < :start + INTERVAL '1 month'
          AND m.user_id IS NOT NULL
        GROUP BY u.username, u.email, w.name
        ORDER BY cost DESC NULLS LAST
    """), {"start": start})

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["username", "email", "workspace", "calls", "tokens", "cost_usd"])
    for r in rows.fetchall():
        d = dict(r._mapping)
        w.writerow([d["username"], d["email"], d.get("workspace", ""), d["calls"], d.get("tokens") or 0, float(d.get("cost") or 0)])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=staffkm-billing-{start.strftime('%Y-%m')}.csv"},
    )
