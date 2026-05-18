"""Worker heartbeats admin API（v3.6 P2）。

GET /admin/heartbeats — 列所有 worker 心跳，admin only。
非 workspace-scoped — 用 X-User-Roles header 判斷，pattern 同 admin_quota / webhook_outbox。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session

router = APIRouter()


def _require_admin(request: Request) -> None:
    roles = getattr(request.state, "roles", []) or []
    if "admin" not in roles:
        raise HTTPException(status_code=403, detail="需要管理員權限")


@router.get("", response_model=ApiResponse, summary="列出所有 worker heartbeat")
async def list_heartbeats(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    rows = await session.execute(text("""
        SELECT worker_name, pid, host, started_at, last_beat, in_flight,
               EXTRACT(EPOCH FROM (now() - last_beat))::INT AS stale_seconds
        FROM task_heartbeats
        ORDER BY worker_name
    """))
    items = []
    for r in rows.fetchall():
        d = dict(r._mapping)
        d["healthy"] = (d["stale_seconds"] or 0) < 300  # < 5 min
        items.append(d)
    return ApiResponse(data={"items": items, "stale_threshold_sec": 300})
