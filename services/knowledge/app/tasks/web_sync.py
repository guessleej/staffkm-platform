"""Sprint 16 — Celery 任務：抓 URL → 抽文字 → 入 KB。

MVP scope：單一 URL（非全站爬蟲）。後續可加 follow_links / sitemap。
"""
from __future__ import annotations

import asyncio
import uuid

import httpx
import structlog
import trafilatura
from sqlalchemy import text as text_sql
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.core.text_ingest import ingest_text_into_kb
from app.models.knowledge_base import KnowledgeBase
from app.tasks.celery_app import celery_app

log = structlog.get_logger()


@celery_app.task(
    bind=True,
    name="app.tasks.web_sync.sync_web_kb",
    max_retries=2,
    acks_late=True,
)
def sync_web_kb(self, kb_id: str, url: str, workspace_id: str) -> dict:
    """Celery 同步入口。"""
    from staffkm_core.utils.net import UnsafeURLError
    try:
        return asyncio.run(_async_sync(kb_id, url, workspace_id))
    except UnsafeURLError as exc:
        # SSRF 防護擋下：retry 同一 URL 沒意義，直接回失敗（狀態已標 failed）
        log.warning("web_sync_blocked_ssrf", kb_id=kb_id, url=url, error=str(exc))
        return {"ok": False, "url": url, "error": f"URL 被 SSRF 防護擋下：{exc}"}
    except Exception as exc:
        log.error("web_sync_will_retry", kb_id=kb_id, url=url, error=str(exc))
        raise self.retry(exc=exc, countdown=30)


async def _async_sync(kb_id_s: str, url: str, workspace_id_s: str) -> dict:
    kb_id = uuid.UUID(kb_id_s)
    workspace_id = uuid.UUID(workspace_id_s)
    engine = create_async_engine(settings.DB_URL, pool_size=1, max_overflow=0)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _set_status(status: str, error: str | None = None) -> None:
        async with session_factory() as s:
            # 注意：:st 不可同時用在 SET 賦值與 CASE 比較 → asyncpg 對 $1 推斷
            # 不一致型別 AmbiguousParameterError（CLAUDE.md §8 雷）。拆成兩個 param。
            await s.execute(
                text_sql(
                    "UPDATE knowledge_bases SET sync_status = :st, sync_error = :err, "
                    "last_synced_at = CASE WHEN :st_chk = 'ready' THEN now() ELSE last_synced_at END "
                    "WHERE id = :id"
                ),
                {"st": status, "st_chk": status, "err": error, "id": str(kb_id)},
            )
            await s.commit()

    try:
        await _set_status("running")

        # 1. 抓（SSRF guard：驗證初始 URL + 逐跳 redirect 再驗證，擋內網/metadata）
        from staffkm_core.utils.net import safe_request
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={
                "User-Agent": "staffKM-WebSync/1.0 (+https://staffkm.local)"
            },
        ) as client:
            resp = await safe_request(client, "GET", url)
            resp.raise_for_status()
            html = resp.text

        # 2. 抽文字（trafilatura 是最好的 boilerplate-stripper）
        content = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            favor_recall=True,
        ) or ""
        if not content.strip():
            raise ValueError("URL 內容抽取為空（可能是 JS-only 頁面或無實際文字）")

        # 3. 取 title（trafilatura metadata 比 BeautifulSoup 簡單）
        meta = trafilatura.extract_metadata(html)
        title = (getattr(meta, "title", None) if meta else None) or url

        # 4. 寫 KB
        async with session_factory() as session:
            kb = await session.get(KnowledgeBase, kb_id)
            if not kb:
                raise ValueError(f"KB {kb_id} 不存在")
            result = await ingest_text_into_kb(
                session,
                workspace_id=workspace_id,
                kb=kb,
                content=content,
                title=title,
                source=url,
                chunking="auto",
                extra_meta={"web_source": url},
                # 18-C：同 URL 重 sync 不重複建 doc
                upsert_key=f"web:{url}",
            )

        await _set_status("ready")
        log.info("web_sync_done", kb_id=kb_id_s, url=url, paragraphs=result["paragraphs"])
        return {"ok": True, "url": url, **result}

    except Exception as exc:
        await _set_status("failed", error=str(exc)[:500])
        raise
    finally:
        await engine.dispose()
