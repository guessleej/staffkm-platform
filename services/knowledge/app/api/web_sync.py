"""Sprint 16 — Web KB 同步 API。

POST /knowledge/bases/{kb_id}/web-sync   啟動單次同步
GET  /knowledge/bases/{kb_id}/sync-info  查詢同步狀態
"""
from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import KnowledgeBase
from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import (
    TenantContext, WorkspaceScopedQuery, require_member, require_writer,
)

router = APIRouter()

_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


class WebSyncReq(BaseModel):
    url: str = Field(..., min_length=8, max_length=2048)

    @field_validator("url")
    @classmethod
    def _check_url(cls, v: str) -> str:
        if not _URL_RE.match(v):
            raise ValueError("URL 必須以 http:// 或 https:// 開頭")
        return v.strip()


class WebSyncBatchReq(BaseModel):
    """18-C：多 URL 批次（一次最多 20 個，避免被當作 crawler 濫用）。"""
    urls: list[str] = Field(..., min_length=1, max_length=20)

    @field_validator("urls")
    @classmethod
    def _check_urls(cls, v: list[str]) -> list[str]:
        cleaned: list[str] = []
        for u in v:
            u = (u or "").strip()
            if not u:
                continue
            if not _URL_RE.match(u):
                raise ValueError(f"URL 必須以 http:// 或 https:// 開頭：{u[:60]}")
            cleaned.append(u)
        if not cleaned:
            raise ValueError("至少需要 1 個有效 URL")
        # 去重保序
        seen: set[str] = set()
        out: list[str] = []
        for u in cleaned:
            if u not in seen:
                seen.add(u); out.append(u)
        return out


@router.post("/{kb_id}/web-sync", response_model=ApiResponse)
async def trigger_web_sync(
    kb_id: uuid.UUID,
    body: WebSyncReq,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    """記下 URL + 排程 celery 抓取任務。不阻塞 request。"""
    q = WorkspaceScopedQuery(KnowledgeBase).select().where(KnowledgeBase.id == kb_id)
    kb = (await session.execute(q)).scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="知識庫不存在或不屬於此工作區")

    # 標記 KB 為 web 型 + 紀錄 source_url + 重設 sync_status
    await session.execute(
        text(
            "UPDATE knowledge_bases SET "
            "  source_type = 'web', source_url = :u, "
            "  sync_status = 'pending', sync_error = NULL, updated_at = now() "
            "WHERE id = :id AND workspace_id = :ws"
        ),
        {"u": body.url, "id": str(kb_id), "ws": str(ctx.workspace_id)},
    )
    await session.commit()

    # 排程任務（lazy-import 避免 web 啟動時就拉 trafilatura）
    from app.tasks.web_sync import sync_web_kb
    task_id: str | None = None
    try:
        task = sync_web_kb.apply_async(
            args=[str(kb_id), body.url, str(ctx.workspace_id)],
            countdown=1,
        )
        task_id = task.id
    except Exception:
        pass  # broker 掛了不阻擋 API，使用者可手動重觸發

    return ApiResponse(
        message="已啟動同步，請稍候重新整理頁面",
        data={"kb_id": str(kb_id), "url": body.url, "task_id": task_id},
    )


@router.post("/{kb_id}/web-sync/batch", response_model=ApiResponse)
async def trigger_web_sync_batch(
    kb_id: uuid.UUID,
    body: WebSyncBatchReq,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    """18-C：一次排程多個 URL 抓取（最多 20）。每個 URL 變成獨立 celery 任務。

    KB 標為 web 型；source_url 改存 JSON 陣列（首個 URL 為主顯示）。
    """
    q = WorkspaceScopedQuery(KnowledgeBase).select().where(KnowledgeBase.id == kb_id)
    kb = (await session.execute(q)).scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="知識庫不存在或不屬於此工作區")

    primary_url = body.urls[0]
    await session.execute(
        text(
            "UPDATE knowledge_bases SET "
            "  source_type = 'web', source_url = :u, "
            "  sync_status = 'pending', sync_error = NULL, updated_at = now() "
            "WHERE id = :id AND workspace_id = :ws"
        ),
        {"u": primary_url, "id": str(kb_id), "ws": str(ctx.workspace_id)},
    )
    await session.commit()

    from app.tasks.web_sync import sync_web_kb
    task_ids: list[str] = []
    for i, u in enumerate(body.urls):
        try:
            task = sync_web_kb.apply_async(
                args=[str(kb_id), u, str(ctx.workspace_id)],
                countdown=1 + i,  # 錯開派發，避免同時打爆對方
            )
            task_ids.append(task.id)
        except Exception:
            pass

    return ApiResponse(
        message=f"已排程 {len(body.urls)} 個 URL 同步",
        data={"kb_id": str(kb_id), "url_count": len(body.urls), "task_ids": task_ids},
    )


@router.get("/{kb_id}/sync-info", response_model=ApiResponse)
async def get_sync_info(
    kb_id: uuid.UUID,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    """回傳 KB source_type / source_url / sync_status / last_synced_at / sync_error。"""
    r = await session.execute(
        text(
            "SELECT source_type, source_url, sync_status, sync_error, last_synced_at "
            "FROM knowledge_bases WHERE id = :id AND workspace_id = :ws"
        ),
        {"id": str(kb_id), "ws": str(ctx.workspace_id)},
    )
    row = r.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="知識庫不存在")
    m = row._mapping
    return ApiResponse(data={
        "source_type":   m.get("source_type") or "manual",
        "source_url":    m.get("source_url"),
        "sync_status":   m.get("sync_status"),
        "sync_error":    m.get("sync_error"),
        "last_synced_at": m.get("last_synced_at").isoformat() if m.get("last_synced_at") else None,
    })
