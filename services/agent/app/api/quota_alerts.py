"""Quota Alert CRUD API（v3.3 D2）。

workspace-scoped；admin 才能管理。每個 alert = scope + threshold_pct + channel + target。
worker（quota_alert_worker.py）會定期 evaluate 並依 channel 發通知。
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_admin

router = APIRouter()


class QuotaAlertCreate(BaseModel):
    scope:         str  = Field(..., pattern="^(workspace|user)$")
    threshold_pct: int  = Field(..., ge=1, le=100)
    channel:       str  = Field(..., pattern="^(email|slack|webhook)$")
    target:        str  = Field(..., min_length=1)
    enabled:       bool = True


class QuotaAlertUpdate(BaseModel):
    scope:         str | None  = Field(None, pattern="^(workspace|user)$")
    threshold_pct: int | None  = Field(None, ge=1, le=100)
    channel:       str | None  = Field(None, pattern="^(email|slack|webhook)$")
    target:        str | None  = None
    enabled:       bool | None = None


@router.get("", response_model=ApiResponse, summary="列出 workspace 的 quota alerts")
async def list_alerts(
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    rows = await session.execute(text("""
        SELECT id, workspace_id, scope, threshold_pct, channel, target, enabled, created_at
        FROM quota_alerts
        WHERE workspace_id = :ws
        ORDER BY created_at DESC
    """), {"ws": str(ctx.workspace_id)})
    items = []
    for r in rows.fetchall():
        d = dict(r._mapping)
        d["id"] = str(d["id"])
        d["workspace_id"] = str(d["workspace_id"])
        if d.get("created_at") is not None:
            d["created_at"] = d["created_at"].isoformat()
        items.append(d)
    return ApiResponse(data={"items": items})


@router.post("", response_model=ApiResponse, summary="建立 quota alert")
async def create_alert(
    body: QuotaAlertCreate,
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    new_id = uuid.uuid4()
    await session.execute(text("""
        INSERT INTO quota_alerts (id, workspace_id, scope, threshold_pct, channel, target, enabled)
        VALUES (:id, :ws, :scope, :pct, :channel, :target, :enabled)
    """), {
        "id": str(new_id), "ws": str(ctx.workspace_id),
        "scope": body.scope, "pct": body.threshold_pct,
        "channel": body.channel, "target": body.target, "enabled": body.enabled,
    })
    await session.commit()
    return ApiResponse(data={"id": str(new_id)}, message="alert created")


@router.put("/{alert_id}", response_model=ApiResponse, summary="更新 quota alert")
async def update_alert(
    body: QuotaAlertUpdate,
    alert_id: uuid.UUID = Path(...),
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        return ApiResponse(message="nothing to update")
    sets = ", ".join(f"{k} = :{k}" for k in fields.keys())
    params = {**fields, "id": str(alert_id), "ws": str(ctx.workspace_id)}
    # 對映 pydantic field → SQL column（threshold_pct 等同名）
    result = await session.execute(
        text(f"UPDATE quota_alerts SET {sets} WHERE id = :id AND workspace_id = :ws"),
        params,
    )
    await session.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="alert not found")
    return ApiResponse(message="alert updated")


@router.delete("/{alert_id}", response_model=ApiResponse, summary="刪除 quota alert")
async def delete_alert(
    alert_id: uuid.UUID = Path(...),
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        text("DELETE FROM quota_alerts WHERE id = :id AND workspace_id = :ws"),
        {"id": str(alert_id), "ws": str(ctx.workspace_id)},
    )
    await session.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="alert not found")
    return ApiResponse(message="alert deleted")
