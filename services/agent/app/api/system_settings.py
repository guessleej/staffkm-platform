"""System settings — v5.0.1 admin

非 workspace-scoped；用 X-User-Roles 判 admin（同 admin_quota pattern）。

注意：目前 settings 是 **advisory**。embedding model / RRF weight 等實際 runtime
仍由 env / per-call body 決定。將 settings 接到 runtime 留 v5.x。
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session

router = APIRouter()


def require_admin_role(request: Request) -> str | None:
    roles = getattr(request.state, "roles", []) or []
    if "admin" not in roles:
        raise HTTPException(status_code=403, detail="需要管理員權限")
    return getattr(request.state, "user_id", None)


class SettingUpdate(BaseModel):
    value: Any


def _row_to_dict(r: Any) -> dict:
    d = dict(r._mapping)
    if d.get("updated_by") is not None:
        d["updated_by"] = str(d["updated_by"])
    return d


@router.get("", response_model=ApiResponse, summary="列出全部 system settings")
async def list_settings(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    require_admin_role(request)
    rows = await session.execute(text(
        "SELECT key, value, description, updated_at, updated_by FROM system_settings ORDER BY key"
    ))
    items = [_row_to_dict(r) for r in rows.fetchall()]
    return ApiResponse(data={"items": items})


@router.get("/{key}", response_model=ApiResponse, summary="取得單一 setting")
async def get_setting(
    request: Request,
    key: str = Path(..., min_length=1, max_length=64),
    session: AsyncSession = Depends(get_session),
):
    # 此 endpoint 給 admin UI 即時 refresh；其他 service 內部讀則直接打 DB。
    require_admin_role(request)
    row = (await session.execute(
        text("SELECT key, value, description, updated_at, updated_by FROM system_settings WHERE key = :k"),
        {"k": key},
    )).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="setting 不存在")
    return ApiResponse(data=_row_to_dict(row))


@router.put("/{key}", response_model=ApiResponse, summary="更新單一 setting")
async def update_setting(
    request: Request,
    body: SettingUpdate,
    key: str = Path(..., min_length=1, max_length=64),
    session: AsyncSession = Depends(get_session),
):
    actor_user_id = require_admin_role(request)
    # value 任意 JSON — 序列化後存進 jsonb（避開 asyncpg dialect bug，用 CAST）
    value_json = json.dumps(body.value)
    res = await session.execute(text("""
        UPDATE system_settings
           SET value      = CAST(:val AS jsonb),
               updated_at = now(),
               updated_by = CAST(:by AS uuid)
         WHERE key = :k
    """), {"val": value_json, "by": actor_user_id, "k": key})
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="setting 不存在")
    await session.commit()
    return ApiResponse(message="設定已更新")
