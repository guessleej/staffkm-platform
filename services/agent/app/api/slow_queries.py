"""Slow query explains admin API (v3.8 P4).

讀取 v3.8 P4 自動捕獲的 slow query plan tree。admin 角色限定。
"""
from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, Path, Query, Request, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session

router = APIRouter()


def _require_admin(request: Request) -> None:
    roles = getattr(request.state, "roles", []) or []
    if "admin" not in roles:
        raise HTTPException(status_code=403, detail="admin only")


@router.get("", response_model=ApiResponse, summary="列出最近 slow query (24h)")
async def list_slow_queries(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    rows = await session.execute(text("""
        SELECT id, captured_at, duration_ms, sql_text, sql_hash, explain_error,
               (explain_json IS NOT NULL) AS has_plan
        FROM slow_query_explains
        WHERE captured_at >= now() - INTERVAL '24 hours'
        ORDER BY duration_ms DESC, captured_at DESC
        LIMIT :lim
    """), {"lim": limit})
    return ApiResponse(data={"items": [dict(r._mapping) for r in rows.fetchall()]})


# NOTE: 必須在 /{explain_id} 之前註冊，否則 'top-by-hash' 會被當成 UUID 解析失敗
@router.get("/top-by-hash", response_model=ApiResponse, summary="aggregate by sql_hash (24h)")
async def top_by_hash(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    rows = await session.execute(text("""
        SELECT sql_hash,
               COUNT(*)::INT AS occurrences,
               MAX(duration_ms) AS max_ms,
               AVG(duration_ms)::INT AS avg_ms,
               MIN(sql_text) AS sample_sql
        FROM slow_query_explains
        WHERE captured_at >= now() - INTERVAL '24 hours'
        GROUP BY sql_hash
        ORDER BY occurrences DESC, max_ms DESC
        LIMIT 50
    """))
    return ApiResponse(data={"items": [dict(r._mapping) for r in rows.fetchall()]})


@router.get("/{explain_id}", response_model=ApiResponse, summary="取完整 explain plan")
async def get_explain(
    request: Request,
    explain_id: uuid.UUID = Path(...),
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    r = await session.execute(text("""
        SELECT id, captured_at, duration_ms, sql_text, sql_hash,
               explain_json, explain_error
        FROM slow_query_explains
        WHERE id = :id
    """), {"id": str(explain_id)})
    row = r.fetchone()
    if not row:
        raise HTTPException(404, "explain not found")
    return ApiResponse(data=dict(row._mapping))
