"""Long-term Memory API（M4 啟動）。

- GET    /memories                  分頁列出（依 scope / user / app 過濾）
- POST   /memories                  新增記憶
- DELETE /memories/{id}             刪除單筆
- POST   /memories/search           關鍵字 / 全文搜尋（含 access_count++）

scope:
  - user：本人專屬（user_id = ctx.user_id）
  - app：綁定特定 application（任何成員可讀）
  - team：workspace 全體共享

讀取規則：
  - user 範圍只看到自己的紀錄
  - app / team 範圍：require_member 即可讀
寫入規則：
  - user 範圍任何人可寫自己的
  - app / team 範圍要 require_writer（editor 以上）
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_member, require_writer

router = APIRouter()


_VALID_SCOPES = ("user", "app", "team")


class MemoryCreate(BaseModel):
    content:        str  = Field(..., min_length=1, max_length=10_000)
    scope:          str  = Field(default="user")
    application_id: str | None = None
    tags:           list[str]  = Field(default_factory=list)
    importance:     int = Field(default=5, ge=1, le=10)


class MemorySearch(BaseModel):
    query:          str  = Field(..., min_length=1, max_length=512)
    scope:          str | None = None
    application_id: str | None = None
    top_k:          int  = Field(default=5, ge=1, le=50)


def _check_scope(scope: str) -> None:
    if scope not in _VALID_SCOPES:
        raise HTTPException(status_code=400, detail=f"scope 必須為 {_VALID_SCOPES} 之一")


def _scope_predicate(ctx: TenantContext, scope: str | None) -> tuple[str, dict[str, Any]]:
    """組裝 WHERE 子句與 params（依 scope 過濾），保證跨用戶不外洩。"""
    base = "workspace_id = :ws"
    params: dict[str, Any] = {"ws": str(ctx.workspace_id)}
    if scope == "user":
        base += " AND scope = 'user' AND user_id = :uid"
        params["uid"] = str(ctx.user_id)
    elif scope == "app":
        base += " AND scope = 'app'"
    elif scope == "team":
        base += " AND scope = 'team'"
    else:
        # 不指定 → 全部本人可看的：user(自己) + app + team
        base += " AND (scope IN ('app','team') OR (scope = 'user' AND user_id = :uid))"
        params["uid"] = str(ctx.user_id)
    return base, params


@router.get("", response_model=ApiResponse, summary="列出記憶")
async def list_memories(
    scope: str | None = Query(default=None, description="user|app|team；省略 = 全部本人可見"),
    application_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    if scope:
        _check_scope(scope)
    where, params = _scope_predicate(ctx, scope)
    if application_id:
        where += " AND application_id = :app"
        params["app"] = application_id
    params["lim"] = page_size
    params["off"] = (page - 1) * page_size
    rows = await session.execute(
        text(f"""
            SELECT id, user_id, application_id, scope, content, tags, importance,
                   access_count, last_accessed_at, created_at
            FROM long_term_memories
            WHERE {where}
            ORDER BY importance DESC, created_at DESC
            LIMIT :lim OFFSET :off
        """),
        params,
    )
    items = [dict(r._mapping) for r in rows.fetchall()]
    return ApiResponse(data={"items": items, "page": page, "page_size": page_size})


@router.post("", response_model=ApiResponse, summary="新增記憶")
async def create_memory(
    body: MemoryCreate,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    _check_scope(body.scope)
    # app / team 範圍須有 editor 權限
    if body.scope in ("app", "team"):
        # 簡化：role 字串檢查；正式可注入 require_writer
        if ctx.role.value not in ("owner", "admin", "editor"):
            raise HTTPException(status_code=403, detail="app / team 範圍記憶需 editor 以上權限")

    import json as _json
    mid = str(uuid.uuid4())
    await session.execute(
        text("""
            INSERT INTO long_term_memories (
                id, workspace_id, user_id, application_id, scope, content,
                tags, importance, created_by
            ) VALUES (
                :id, :ws, :uid, :app, :scope, :content,
                :tags::jsonb, :imp, :by
            )
        """),
        {
            "id":      mid,
            "ws":      str(ctx.workspace_id),
            "uid":     str(ctx.user_id) if body.scope == "user" else None,
            "app":     body.application_id,
            "scope":   body.scope,
            "content": body.content,
            "tags":    _json.dumps(body.tags, ensure_ascii=False),
            "imp":     body.importance,
            "by":      str(ctx.user_id),
        },
    )
    return ApiResponse(data={"id": mid}, message="記憶已建立")


@router.delete("/{memory_id}", response_model=ApiResponse, summary="刪除記憶")
async def delete_memory(
    memory_id: uuid.UUID,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    # 只能刪自己的（user 範圍）或具 editor 權限可刪 app / team
    r = await session.execute(
        text("SELECT scope, user_id FROM long_term_memories WHERE id = :id AND workspace_id = :ws"),
        {"id": str(memory_id), "ws": str(ctx.workspace_id)},
    )
    row = r.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="記憶不存在")
    rec = dict(row._mapping)
    if rec["scope"] == "user":
        if str(rec["user_id"]) != str(ctx.user_id):
            raise HTTPException(status_code=403, detail="只能刪除自己的記憶")
    else:
        if ctx.role.value not in ("owner", "admin", "editor"):
            raise HTTPException(status_code=403, detail="刪除 app/team 記憶需 editor 以上權限")
    await session.execute(
        text("DELETE FROM long_term_memories WHERE id = :id AND workspace_id = :ws"),
        {"id": str(memory_id), "ws": str(ctx.workspace_id)},
    )
    return ApiResponse(message="記憶已刪除")


@router.post("/search", response_model=ApiResponse, summary="搜尋記憶（關鍵字 / 全文）")
async def search_memories(
    body: MemorySearch,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    if body.scope:
        _check_scope(body.scope)
    where, params = _scope_predicate(ctx, body.scope)
    if body.application_id:
        where += " AND application_id = :app"
        params["app"] = body.application_id
    # 全文檢索（'simple' 配置；中文使用者可改 'chinese' / pg_trgm）
    where += " AND to_tsvector('simple', content) @@ plainto_tsquery('simple', :q)"
    params["q"] = body.query
    params["lim"] = body.top_k

    rows = await session.execute(
        text(f"""
            SELECT id, user_id, application_id, scope, content, tags, importance,
                   access_count, last_accessed_at, created_at,
                   ts_rank(to_tsvector('simple', content), plainto_tsquery('simple', :q)) AS rank
            FROM long_term_memories
            WHERE {where}
            ORDER BY rank DESC, importance DESC, created_at DESC
            LIMIT :lim
        """),
        params,
    )
    items = [dict(r._mapping) for r in rows.fetchall()]

    # bump access_count / last_accessed_at
    if items:
        ids = [str(i["id"]) for i in items]
        await session.execute(
            text(
                "UPDATE long_term_memories SET access_count = access_count + 1, "
                "last_accessed_at = :now WHERE id::text = ANY(:ids)"
            ),
            {"ids": ids, "now": datetime.utcnow()},
        )

    return ApiResponse(data=items)
