"""Celery 背景任務：對文件 / KB 建知識圖譜（RFC-014 GraphRAG MVP v5.11.0）。

抽取用地端 GRAPH_EXTRACT_MODEL（gemma4:e4b），不阻塞入庫、失敗不影響既有 RAG。
- doc_id 指定 → 只建該文件（process_document 入庫後 hook 用）
- doc_id=None → 重建整個 KB（rebuild 端點用）
"""
import asyncio

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.core.graph import build_communities, build_graph_for_document
from app.tasks.celery_app import celery_app

log = structlog.get_logger()


@celery_app.task(
    bind=True,
    name="app.tasks.build_graph.build_graph",
    max_retries=2,
    acks_late=True,
)
def build_graph(self, kb_id: str, workspace_id: str, doc_id: str | None = None) -> dict:
    try:
        return asyncio.run(_run(kb_id, workspace_id, doc_id))
    except Exception as exc:
        countdown = min(30 * (2 ** self.request.retries), 300)
        log.error("build_graph_will_retry", kb_id=kb_id, error=str(exc), countdown=countdown)
        raise self.retry(exc=exc, countdown=countdown)


async def _run(kb_id: str, workspace_id: str, doc_id: str | None) -> dict:
    engine = create_async_engine(settings.DB_URL, pool_size=1, max_overflow=0)
    sf = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sf() as session:
            if doc_id:
                doc_ids = [doc_id]
            else:
                rows = await session.execute(
                    text("SELECT id FROM documents WHERE knowledge_base_id = :kb"),
                    {"kb": kb_id},
                )
                doc_ids = [str(r[0]) for r in rows.fetchall()]
            total_e = total_m = total_r = 0
            for d in doc_ids:
                r = await build_graph_for_document(session, d, kb_id, workspace_id)
                total_e += r["entities"]
                total_m += r["mentions"]
                total_r += r.get("relations", 0)
            # Phase 3：full rebuild（doc_id=None）收尾建社群（需全 KB 關係）
            communities = 0
            if doc_id is None:
                communities = (await build_communities(session, kb_id, workspace_id)).get("communities", 0)
            log.info("build_graph_done", kb_id=kb_id, docs=len(doc_ids),
                     entities=total_e, mentions=total_m, relations=total_r, communities=communities)
            return {"docs": len(doc_ids), "entities": total_e, "mentions": total_m,
                    "relations": total_r, "communities": communities}
    finally:
        await engine.dispose()
