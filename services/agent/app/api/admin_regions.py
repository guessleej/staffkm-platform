"""Admin API: regions registry + conflicts viewer + workspace region binding.

v5.0 K — active-active multi-region scaffolding.
"""
from __future__ import annotations
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session

router = APIRouter()


def _require_admin(request: Request) -> None:
    roles = getattr(request.state, "roles", []) or []
    if "admin" not in roles:
        raise HTTPException(403, "admin only")


# ── Regions registry ──────────────────────────────────────────────

class RegionCreate(BaseModel):
    id: str
    name: str
    db_url: str | None = None
    minio_endpoint: str | None = None


@router.get("/regions", response_model=ApiResponse, summary="List configured regions")
async def list_regions(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    rows = await session.execute(text("""
        SELECT id, name, db_url, minio_endpoint, is_active, created_at
        FROM regions
        ORDER BY id
    """))
    return ApiResponse(data={"items": [dict(r._mapping) for r in rows.fetchall()]})


@router.post("/regions", response_model=ApiResponse, summary="Register or update a region")
async def create_region(
    request: Request,
    body: RegionCreate,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    await session.execute(text("""
        INSERT INTO regions (id, name, db_url, minio_endpoint)
        VALUES (:id, :n, :db, :mi)
        ON CONFLICT (id) DO UPDATE
        SET name = EXCLUDED.name,
            db_url = EXCLUDED.db_url,
            minio_endpoint = EXCLUDED.minio_endpoint
    """), {
        "id": body.id, "n": body.name,
        "db": body.db_url, "mi": body.minio_endpoint,
    })
    await session.commit()
    return ApiResponse(message="region registered")


@router.delete("/regions/{region_id}", response_model=ApiResponse, summary="Deactivate a region")
async def delete_region(
    request: Request,
    region_id: str = Path(...),
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    # 不真刪，set is_active=false（FK 還在指）
    await session.execute(
        text("UPDATE regions SET is_active = FALSE WHERE id = :id"),
        {"id": region_id},
    )
    await session.commit()
    return ApiResponse(message=f"region {region_id} deactivated")


# ── Conflicts ─────────────────────────────────────────────────────

@router.get("/conflicts", response_model=ApiResponse, summary="List recent conflicts")
async def list_conflicts(
    request: Request,
    status: str | None = Query(None, description="pending | resolved | (omit = all)"),
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    where = []
    params: dict = {"lim": limit}
    if status == "pending":
        where.append("resolution = 'pending'")
    elif status == "resolved":
        where.append("resolution IS NOT NULL AND resolution != 'pending'")
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    rows = await session.execute(text(f"""
        SELECT id, detected_at, entity_type, entity_id,
               region_a, region_b, value_a, value_b,
               resolution, resolved_value, resolved_at
        FROM region_conflict_log
        {where_sql}
        ORDER BY detected_at DESC
        LIMIT :lim
    """), params)
    return ApiResponse(data={"items": [dict(r._mapping) for r in rows.fetchall()]})


class ResolveBody(BaseModel):
    resolution: str  # 'lww' | 'merge' | 'manual'
    resolved_value: dict | None = None


@router.post(
    "/conflicts/{conflict_id}/resolve",
    response_model=ApiResponse,
    summary="Manually resolve a conflict",
)
async def resolve_conflict(
    request: Request,
    body: ResolveBody,
    conflict_id: uuid.UUID = Path(...),
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    if body.resolution not in ("lww", "merge", "manual"):
        raise HTTPException(400, "resolution must be lww | merge | manual")
    r = await session.execute(text("""
        UPDATE region_conflict_log
        SET resolution = :r,
            resolved_value = CAST(:v AS jsonb),
            resolved_at = now()
        WHERE id = :id
        RETURNING id
    """), {
        "r": body.resolution,
        "v": json.dumps(body.resolved_value) if body.resolved_value is not None else None,
        "id": str(conflict_id),
    })
    if not r.fetchone():
        raise HTTPException(404, "conflict not found")
    await session.commit()
    return ApiResponse(message="conflict resolved")


# ── Workspace region binding ──────────────────────────────────────

class BindRegionBody(BaseModel):
    primary_region: str


@router.put(
    "/workspaces/{workspace_id}/region",
    response_model=ApiResponse,
    summary="Bind workspace to a primary region (L1 region-pin)",
)
async def bind_region(
    request: Request,
    body: BindRegionBody,
    workspace_id: uuid.UUID = Path(...),
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    r = await session.execute(text("""
        UPDATE workspace SET primary_region = :r WHERE id = :id RETURNING id
    """), {"r": body.primary_region, "id": str(workspace_id)})
    if not r.fetchone():
        raise HTTPException(404, "workspace not found")
    await session.commit()
    return ApiResponse(message=f"workspace bound to region {body.primary_region}")
