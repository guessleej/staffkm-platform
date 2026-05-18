"""Workspace 自訂 App 模板 API（Sprint 19.x）。

- GET    /app-templates           列出 workspace 內所有自訂模板（不含 built-in）
- POST   /app-templates           新增（require_writer）
- PUT    /app-templates/{id}      更新（require_writer）
- DELETE /app-templates/{id}      刪除（require_writer）

Built-in templates 寫死在前端 data/appTemplates.ts；workspace 模板補充而已。
"""
from __future__ import annotations

import json as _json
import uuid
from datetime import datetime
from typing import Any

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.audit import _record
from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_member, require_writer

logger = logging.getLogger(__name__)
router = APIRouter()


async def _safe_audit(session: AsyncSession, **kwargs) -> None:
    try:
        await _record(session, **kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.warning("audit record failed: %s", exc)


class TemplateCreate(BaseModel):
    name:                str  = Field(..., min_length=1, max_length=128)
    emoji:               str  = Field(default='✨', max_length=8)
    description:         str  = ''
    system_prompt:       str  = ''
    welcome_message:     str  = ''
    suggested_questions: list[str] = Field(default_factory=list)
    requires_kb:         bool = False
    is_public:           bool = False        # v2.5-C：marketplace 開放分享


class TemplateUpdate(BaseModel):
    name:                str | None = None
    emoji:               str | None = None
    description:         str | None = None
    system_prompt:       str | None = None
    welcome_message:     str | None = None
    suggested_questions: list[str] | None = None
    requires_kb:         bool | None = None
    is_public:           bool | None = None


class TemplateOut(BaseModel):
    id:                  str
    name:                str
    emoji:               str
    description:         str
    system_prompt:       str
    welcome_message:     str
    suggested_questions: list[str]
    requires_kb:         bool
    is_public:           bool = False
    install_count:       int = 0
    created_at:          datetime
    updated_at:          datetime


def _row_to_out(row) -> TemplateOut:
    m = dict(row._mapping)
    sq = m.get('suggested_questions') or []
    if isinstance(sq, str):
        try: sq = _json.loads(sq)
        except Exception: sq = []
    return TemplateOut(
        id=str(m['id']),
        name=m.get('name') or '',
        emoji=m.get('emoji') or '✨',
        description=m.get('description') or '',
        system_prompt=m.get('system_prompt') or '',
        welcome_message=m.get('welcome_message') or '',
        suggested_questions=sq,
        requires_kb=bool(m.get('requires_kb')),
        is_public=bool(m.get('is_public')),
        install_count=int(m.get('install_count') or 0),
        created_at=m.get('created_at') or datetime.utcnow(),
        updated_at=m.get('updated_at') or datetime.utcnow(),
    )


@router.get("", response_model=ApiResponse, summary="列出 workspace 自訂 app 模板")
async def list_templates(
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    rows = await session.execute(
        text("""
            SELECT id, name, emoji, description, system_prompt, welcome_message,
                   suggested_questions, requires_kb, is_public, install_count,
                   created_at, updated_at
            FROM workspace_app_templates
            WHERE workspace_id = :ws
            ORDER BY created_at DESC
        """),
        {"ws": str(ctx.workspace_id)},
    )
    return ApiResponse(data=[_row_to_out(r).model_dump() for r in rows.fetchall()])


@router.get("/marketplace", response_model=ApiResponse, summary="v2.5-C：所有 workspace 公開模板")
async def list_marketplace(
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    """跨 workspace 列出所有 is_public=true 模板。按 install_count 排序。
    不顯示自己 workspace 的（避免重複，他們從一般列表已看到）。"""
    rows = await session.execute(
        text("""
            SELECT id, name, emoji, description, system_prompt, welcome_message,
                   suggested_questions, requires_kb, is_public, install_count,
                   created_at, updated_at
            FROM workspace_app_templates
            WHERE is_public = true AND workspace_id != :ws
            ORDER BY install_count DESC, created_at DESC
            LIMIT 100
        """),
        {"ws": str(ctx.workspace_id)},
    )
    return ApiResponse(data=[_row_to_out(r).model_dump() for r in rows.fetchall()])


@router.post("/marketplace/{template_id}/install", response_model=ApiResponse, summary="v2.5-C：安裝 marketplace 模板到自己 workspace")
async def install_marketplace_template(
    template_id: uuid.UUID,
    request: Request,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    # 1. 抓原模板（必須 is_public）
    src = await session.execute(
        text("""
            SELECT name, emoji, description, system_prompt, welcome_message,
                   suggested_questions, requires_kb, workspace_id
            FROM workspace_app_templates
            WHERE id = :id AND is_public = true
        """),
        {"id": str(template_id)},
    )
    row = src.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="模板不存在或未公開")
    m = dict(row._mapping)

    # 2. 在自己 workspace 開新模板（is_public=false 預設）
    new_id = uuid.uuid4()
    sq = m.get('suggested_questions') or []
    if isinstance(sq, list):
        sq_json = _json.dumps(sq, ensure_ascii=False)
    else:
        sq_json = sq
    await session.execute(
        text("""
            INSERT INTO workspace_app_templates (
                id, workspace_id, name, emoji, description, system_prompt,
                welcome_message, suggested_questions, requires_kb,
                created_at, updated_at, created_by
            ) VALUES (
                :id, :ws, :name, :emoji, :desc, :sp,
                :wm, CAST(:sq AS jsonb), :req,
                now(), now(), :by
            )
        """),
        {
            "id": str(new_id), "ws": str(ctx.workspace_id),
            "name": m['name'] + ' (從 marketplace)',
            "emoji": m.get('emoji') or '✨',
            "desc": m.get('description') or '',
            "sp": m.get('system_prompt') or '',
            "wm": m.get('welcome_message') or '',
            "sq": sq_json,
            "req": bool(m.get('requires_kb')),
            "by": str(ctx.user_id) if ctx.user_id else None,
        },
    )

    # 3. install_count++（原模板）
    await session.execute(
        text("UPDATE workspace_app_templates SET install_count = install_count + 1 WHERE id = :id"),
        {"id": str(template_id)},
    )

    await _safe_audit(
        session,
        workspace_id=ctx.workspace_id,
        actor_user_id=ctx.user_id,
        actor_username=None,
        action="install_from_marketplace",
        entity_type="template",
        entity_id=str(template_id),
        entity_label=m.get('name'),
        detail={"source_workspace": str(m.get('workspace_id')) if m.get('workspace_id') else None,
                "installed_as": str(new_id)},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()

    return ApiResponse(data={"id": str(new_id)}, message="已安裝到你的 workspace 模板庫")


@router.post("", response_model=ApiResponse, summary="新增自訂模板")
async def create_template(
    body: TemplateCreate,
    request: Request,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    new_id = uuid.uuid4()
    await session.execute(
        text("""
            INSERT INTO workspace_app_templates (
                id, workspace_id, name, emoji, description, system_prompt,
                welcome_message, suggested_questions, requires_kb,
                created_at, updated_at, created_by
            ) VALUES (
                :id, :ws, :name, :emoji, :desc, :sp,
                :wm, CAST(:sq AS jsonb), :req,
                now(), now(), :by
            )
        """),
        {
            "id": str(new_id),
            "ws": str(ctx.workspace_id),
            "name": body.name,
            "emoji": body.emoji,
            "desc": body.description,
            "sp": body.system_prompt,
            "wm": body.welcome_message,
            "sq": _json.dumps(body.suggested_questions, ensure_ascii=False),
            "req": body.requires_kb,
            "by": str(ctx.user_id) if ctx.user_id else None,
        },
    )
    await _safe_audit(
        session,
        workspace_id=ctx.workspace_id,
        actor_user_id=ctx.user_id,
        actor_username=None,
        action="create",
        entity_type="template",
        entity_id=str(new_id),
        entity_label=body.name,
        detail={"is_public": body.is_public},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    return ApiResponse(data={"id": str(new_id)}, message="模板已新增")


@router.put("/{template_id}", response_model=ApiResponse, summary="更新自訂模板")
async def update_template(
    template_id: uuid.UUID,
    body: TemplateUpdate,
    request: Request,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    sets: list[str] = ["updated_at = now()"]
    params: dict[str, Any] = {"id": str(template_id), "ws": str(ctx.workspace_id)}
    data = body.model_dump(exclude_unset=True)
    field_map = {
        "name": ("name", lambda v: v),
        "emoji": ("emoji", lambda v: v),
        "description": ("description", lambda v: v),
        "system_prompt": ("system_prompt", lambda v: v),
        "welcome_message": ("welcome_message", lambda v: v),
        "suggested_questions": ("suggested_questions", lambda v: _json.dumps(v, ensure_ascii=False)),
        "requires_kb": ("requires_kb", lambda v: v),
        "is_public": ("is_public", lambda v: v),
    }
    for key, val in data.items():
        if key not in field_map: continue
        col, prep = field_map[key]
        if col == "suggested_questions":
            sets.append(f"{col} = CAST(:{col} AS jsonb)")
        else:
            sets.append(f"{col} = :{col}")
        params[col] = prep(val)
    if len(sets) == 1:
        return ApiResponse(message="no-op")
    sql = f"UPDATE workspace_app_templates SET {', '.join(sets)} WHERE id = :id AND workspace_id = :ws"
    res = await session.execute(text(sql), params)
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="模板不存在")
    await _safe_audit(
        session,
        workspace_id=ctx.workspace_id,
        actor_user_id=ctx.user_id,
        actor_username=None,
        action="update",
        entity_type="template",
        entity_id=str(template_id),
        entity_label=data.get("name"),
        detail={"fields": sorted(data.keys())},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    return ApiResponse(message="模板已更新")


@router.delete("/{template_id}", response_model=ApiResponse, summary="刪除自訂模板")
async def delete_template(
    template_id: uuid.UUID,
    request: Request,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    name_row = await session.execute(
        text("SELECT name FROM workspace_app_templates WHERE id = :id AND workspace_id = :ws"),
        {"id": str(template_id), "ws": str(ctx.workspace_id)},
    )
    name_existing = name_row.fetchone()
    res = await session.execute(
        text("DELETE FROM workspace_app_templates WHERE id = :id AND workspace_id = :ws"),
        {"id": str(template_id), "ws": str(ctx.workspace_id)},
    )
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="模板不存在")
    await _safe_audit(
        session,
        workspace_id=ctx.workspace_id,
        actor_user_id=ctx.user_id,
        actor_username=None,
        action="delete",
        entity_type="template",
        entity_id=str(template_id),
        entity_label=name_existing._mapping.get("name") if name_existing else None,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    return ApiResponse(message="模板已刪除")
