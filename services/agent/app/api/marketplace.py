"""Public workflow marketplace — v4.10 J.

跨 org 公開 gallery。READ endpoints 不需登入（gateway PUBLIC_PREFIXES `/api/v1/public/`）；
install 仍走 v2.5 workspace-scoped endpoint；rating 在本檔內檢查 user_id（gateway
帶 JWT 過來時會解 user 到 request.state.user_id，未登入則無）。
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_read_session, get_session

router = APIRouter()


# ── Public (no auth) ─────────────────────────────────────────────────


@router.get("", response_model=ApiResponse, summary="List public templates (paginated)")
async def list_public(
    category: str | None = Query(None),
    tag: str | None = Query(None),
    search: str | None = Query(None),
    sort: str = Query("popular", description="popular | recent | rating"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_read_session),
):
    where = ["is_public = TRUE"]
    params: dict = {"lim": page_size, "off": (page - 1) * page_size}
    if category:
        where.append("category = :cat")
        params["cat"] = category
    if tag:
        # CLAUDE.md §8：JSONB 用 CAST，不用 `::jsonb`
        where.append("tags @> CAST(:tag AS jsonb)")
        params["tag"] = f'["{tag}"]'
    if search:
        where.append("(name ILIKE :s OR description ILIKE :s)")
        params["s"] = f"%{search}%"

    order_by = {
        "popular": "install_count DESC, created_at DESC",
        "recent":  "created_at DESC",
        "rating":  "rating_avg DESC NULLS LAST, install_count DESC",
    }.get(sort, "install_count DESC, created_at DESC")

    rows = await session.execute(text(f"""
        SELECT id, name, description, category, tags, cover_image_url,
               publisher_name, publisher_url, license,
               install_count, verified, rating_avg, rating_count,
               created_at
        FROM workspace_app_templates
        WHERE {' AND '.join(where)}
        ORDER BY {order_by}
        LIMIT :lim OFFSET :off
    """), params)
    items = []
    for r in rows.fetchall():
        d = dict(r._mapping)
        if d.get("rating_avg") is not None:
            d["rating_avg"] = float(d["rating_avg"])
        items.append(d)

    # total count（不算 limit/offset）
    count_params = {k: v for k, v in params.items() if k not in ("lim", "off")}
    count_r = await session.execute(text(f"""
        SELECT COUNT(*) FROM workspace_app_templates WHERE {' AND '.join(where)}
    """), count_params)
    total = int(count_r.scalar_one() or 0)

    return ApiResponse(data={
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
    })


@router.get("/categories", response_model=ApiResponse,
            summary="List all distinct categories with counts")
async def categories(session: AsyncSession = Depends(get_read_session)):
    rows = await session.execute(text("""
        SELECT COALESCE(category, 'uncategorized') AS category, COUNT(*)::INT AS count
        FROM workspace_app_templates
        WHERE is_public = TRUE
        GROUP BY category
        ORDER BY count DESC
    """))
    return ApiResponse(data={"items": [dict(r._mapping) for r in rows.fetchall()]})


@router.get("/{template_id}", response_model=ApiResponse, summary="Get template detail")
async def get_detail(
    template_id: uuid.UUID = Path(...),
    session: AsyncSession = Depends(get_read_session),
):
    r = await session.execute(text("""
        SELECT id, name, description, category, tags, cover_image_url,
               publisher_name, publisher_url, license,
               install_count, verified, rating_avg, rating_count,
               schema_json, created_at, updated_at
        FROM workspace_app_templates
        WHERE id = :id AND is_public = TRUE
    """), {"id": str(template_id)})
    row = r.fetchone()
    if not row:
        raise HTTPException(404, "template not found")
    d = dict(row._mapping)
    if d.get("rating_avg") is not None:
        d["rating_avg"] = float(d["rating_avg"])

    rr = await session.execute(text("""
        SELECT user_id, rating, comment, created_at
        FROM template_ratings WHERE template_id = :id
        ORDER BY created_at DESC LIMIT 5
    """), {"id": str(template_id)})
    d["recent_ratings"] = [dict(r._mapping) for r in rr.fetchall()]

    return ApiResponse(data=d)


# ── Rating (需登入：read user_id from request.state) ─────────────────


class RatingRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


@router.post("/{template_id}/rate", response_model=ApiResponse, summary="Rate a template")
async def rate(
    request: Request,
    body: RatingRequest,
    template_id: uuid.UUID = Path(...),
    session: AsyncSession = Depends(get_session),
):
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(401, "login required")

    await session.execute(text("""
        INSERT INTO template_ratings (template_id, user_id, rating, comment)
        VALUES (:tid, :uid, :r, :c)
        ON CONFLICT (template_id, user_id) DO UPDATE
        SET rating = EXCLUDED.rating, comment = EXCLUDED.comment, created_at = now()
    """), {"tid": str(template_id), "uid": str(user_id), "r": body.rating, "c": body.comment})

    await session.execute(text("""
        UPDATE workspace_app_templates SET
            rating_avg   = (SELECT AVG(rating)::NUMERIC(3,2) FROM template_ratings WHERE template_id = :tid),
            rating_count = (SELECT COUNT(*) FROM template_ratings WHERE template_id = :tid)
        WHERE id = :tid
    """), {"tid": str(template_id)})
    await session.commit()
    return ApiResponse(message="rating saved")
