"""Webhook outbox admin API（v3.6 P1）。

list / retry-now / view detail，admin only（跨 workspace）。
非 workspace-scoped — 用 X-User-Roles header 判斷，pattern 同 admin_quota.py。
"""
from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session

router = APIRouter()


def _require_admin(request: Request) -> None:
    roles = getattr(request.state, "roles", []) or []
    if "admin" not in roles:
        raise HTTPException(status_code=403, detail="需要管理員權限")


@router.get("", response_model=ApiResponse, summary="列出 webhook outbox")
async def list_outbox(
    request: Request,
    status: str | None = Query(default=None, description="pending/in_flight/delivered/failed"),
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    where = "TRUE"
    params: dict = {"lim": limit}
    if status:
        where = "status = :status"
        params["status"] = status
    rows = await session.execute(text(f"""
        SELECT id, url, method, status, attempts, next_retry_at,
               last_error, last_status_code, source_type, source_id,
               workspace_id, created_at, delivered_at
        FROM webhook_outbox
        WHERE {where}
        ORDER BY created_at DESC
        LIMIT :lim
    """), params)
    return ApiResponse(data={"items": [dict(r._mapping) for r in rows.fetchall()]})


@router.post("/{outbox_id}/retry", response_model=ApiResponse, summary="立即重試（強制 next_retry_at=now）")
async def retry_now(
    request: Request,
    outbox_id: uuid.UUID = Path(...),
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    # 任何 status 都允許 manual retry (delivered 重發 / failed 從 DLQ 拉回)
    r = await session.execute(text("""
        UPDATE webhook_outbox
        SET status='pending', next_retry_at=now(),
            attempts = CASE WHEN status = 'failed' THEN 0 ELSE attempts END
        WHERE id=:id
        RETURNING id
    """), {"id": str(outbox_id)})
    if not r.fetchone():
        raise HTTPException(404, "outbox row not found")
    await session.commit()
    return ApiResponse(message="re-queued")
