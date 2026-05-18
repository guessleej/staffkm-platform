"""Workflow run history API（v3.5 P1）。

GET /workspace/{ws}/applications/{app_id}/runs              — list runs
GET /workspace/{ws}/applications/{app_id}/runs/{run_id}/steps — list steps
"""
from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_member

router = APIRouter()


@router.get(
    "/{application_id}/runs",
    response_model=ApiResponse,
    summary="列出 application 的 workflow runs",
)
async def list_runs(
    application_id: uuid.UUID = Path(...),
    limit: int = Query(50, ge=1, le=200),
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    rows = await session.execute(text("""
        SELECT r.id, r.fired_at, r.finished_at, r.status, r.output_summary, r.error,
               r.tokens_used, r.cost_usd,
               t.name AS trigger_name
        FROM event_trigger_runs r
        JOIN event_triggers t ON t.id = r.trigger_id
        WHERE r.workspace_id = :ws AND t.application_id = :app
        ORDER BY r.fired_at DESC
        LIMIT :lim
    """), {"ws": str(ctx.workspace_id), "app": str(application_id), "lim": limit})
    items = []
    for r in rows.fetchall():
        d = dict(r._mapping)
        if d.get("cost_usd") is not None:
            d["cost_usd"] = float(d["cost_usd"])
        items.append(d)
    return ApiResponse(data={"items": items})


@router.get(
    "/{application_id}/runs/{run_id}/steps",
    response_model=ApiResponse,
    summary="列出 run 的 steps",
)
async def list_steps(
    application_id: uuid.UUID = Path(...),
    run_id: uuid.UUID = Path(...),
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    # 防越權：驗證 run 屬於這個 workspace + application
    check = await session.execute(text("""
        SELECT 1 FROM event_trigger_runs r
        JOIN event_triggers t ON t.id = r.trigger_id
        WHERE r.id = :rid AND r.workspace_id = :ws AND t.application_id = :app
    """), {"rid": str(run_id), "ws": str(ctx.workspace_id), "app": str(application_id)})
    if not check.fetchone():
        raise HTTPException(404, "run not found")

    rows = await session.execute(text("""
        SELECT id, step_index, node_key, node_type, status,
               input_snapshot, output_snapshot, error, attempts,
               latency_ms, started_at, finished_at
        FROM workflow_run_steps
        WHERE run_id = :rid
        ORDER BY step_index ASC
    """), {"rid": str(run_id)})
    items = [dict(r._mapping) for r in rows.fetchall()]
    return ApiResponse(data={"items": items})
