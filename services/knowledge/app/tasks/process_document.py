"""Celery 背景任務：文件解析 → 分段 → 向量化 → 入庫"""
import asyncio
import io
import uuid
import structlog
from sqlalchemy import delete, select, text as text_sql
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.runtime_models import get_active_embedder
from app.config import settings
from app.core.document_processor import DocumentProcessor
from app.core.chunking import get_chunker
from app.core.storage import download_document
from app.core.vectorstore import upsert_embedding, update_search_vector
from app.models.knowledge_base import Document, Paragraph, DocStatus
from app.tasks.celery_app import celery_app

log = structlog.get_logger()


@celery_app.task(
    bind=True,
    name="app.tasks.process_document.process_document",
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
)
def process_document(self, doc_id: str, minio_key: str, filename: str, inline: bool = False) -> dict:
    """Celery 同步入口，包裝 asyncio 管線。

    inline=True：跳過 minio download / chunking，僅對既有 paragraphs 跑 embedding
    （供 RFC-013 workflow KB inline-write 使用）。
    """
    try:
        return asyncio.run(_async_process(doc_id, minio_key, filename, inline=inline))
    except Exception as exc:
        countdown = min(30 * (2 ** self.request.retries), 300)
        log.error("process_document_will_retry", doc_id=doc_id, error=str(exc), countdown=countdown)
        raise self.retry(exc=exc, countdown=countdown)


async def _async_process(doc_id: str, minio_key: str, filename: str, *, inline: bool = False) -> dict:
    """非同步處理管線：在 Celery worker 的獨立 event loop 中執行。"""
    engine = create_async_engine(settings.DB_URL, pool_size=1, max_overflow=0)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            doc = await session.get(Document, uuid.UUID(doc_id))
            if not doc:
                log.error("document_not_found_in_worker", doc_id=doc_id)
                return {"status": "error", "reason": "not_found"}

            async def set_progress(pct: int, msg: str) -> None:
                doc.meta = {**(doc.meta or {}), "progress": pct, "progress_message": msg}
                await session.commit()

            try:
                doc.status = DocStatus.PROCESSING

                # ── inline 模式（RFC-013）：跳過 download/chunking，僅對既有 paragraphs 跑 embedding ──
                if inline:
                    await set_progress(20, "inline：對既有段落執行向量化…")
                    paras_q = await session.execute(
                        select(Paragraph).where(Paragraph.document_id == doc.id).order_by(Paragraph.order_index)
                    )
                    paras: list[Paragraph] = list(paras_q.scalars().all())
                    if not paras:
                        doc.status = DocStatus.READY
                        await set_progress(100, "inline：無段落可處理")
                        return {"status": "success", "paragraphs": 0, "mode": "inline"}
                    embedder = await get_active_embedder(session)
                    contents = [p.content for p in paras]
                    embeddings = await embedder.embed_batch(contents)
                    # v5.12: 數量不符代表 embedder 丟棄/截斷批次 → zip 會靜默漏向量、文件仍標 READY。
                    if len(embeddings) != len(paras):
                        raise RuntimeError(
                            f"inline embedding 數量不符：{len(embeddings)} != {len(paras)}（疑批次截斷）"
                        )
                    for p, emb in zip(paras, embeddings):
                        await upsert_embedding(session, p.id, doc.knowledge_base_id, emb)
                        await update_search_vector(session, p.id, p.content)
                    doc.status = DocStatus.READY
                    doc.char_count = sum(len(p.content) for p in paras)
                    await set_progress(100, f"inline 處理完成（{len(paras)} 段）")
                    log.info("document_processed_inline", doc_id=doc_id, paragraphs=len(paras))
                    return {"status": "success", "paragraphs": len(paras), "mode": "inline"}

                await set_progress(10, "正在讀取檔案…")

                # 從 MinIO 下載（同步 I/O → 移至執行緒以免卡住 event loop）
                file_bytes = await asyncio.to_thread(download_document, minio_key)

                # 解析文件（vision OCR 模型 / 引擎依 system_settings.default.vision 解析）
                await set_progress(20, "正在解析文件內容…")
                from app.core.runtime_models import resolve_vision_ocr
                ocr_cfg = await resolve_vision_ocr(session)
                processor = DocumentProcessor(**ocr_cfg)
                text = processor.load(io.BytesIO(file_bytes), filename)

                # ── 分段（新版多策略切片系統）──────────────────────
                # 從 KB 設定取出策略；缺值時 fallback auto
                kb_row = await session.execute(
                    text_sql(
                        "SELECT chunk_strategy, chunk_size, chunk_overlap, graph_enabled "
                        "FROM knowledge_bases WHERE id = :id"
                    ),
                    {"id": str(doc.knowledge_base_id)},
                )
                kb_settings = dict(kb_row.fetchone()._mapping) if kb_row else {}
                strategy = kb_settings.get("chunk_strategy") or "auto"
                chunk_size = kb_settings.get("chunk_size") or settings.CHUNK_SIZE
                chunk_overlap = kb_settings.get("chunk_overlap") or settings.CHUNK_OVERLAP

                chunker = get_chunker(strategy, chunk_size, chunk_overlap)
                raw_chunks = chunker.split(text)
                # 把 Chunk dataclass 攤平為「文字 + heading_path 前綴」給 embedding
                chunks: list[str] = []
                chunk_meta: list[dict] = []
                for c in raw_chunks:
                    # heading_path 加入文字，提升 retrieval 對「在 X 章節中」的命中
                    prefix = (" / ".join(c.heading_path) + "\n") if c.heading_path else ""
                    chunks.append(prefix + c.content)
                    chunk_meta.append({
                        "heading_path": c.heading_path,
                        "chunk_type": c.chunk_type,
                        "char_start": c.char_start,
                        "char_end": c.char_end,
                    })
                log.info(
                    "document_chunked",
                    doc_id=doc_id, chunks=len(chunks),
                    strategy=strategy, chunk_size=chunk_size, chunk_overlap=chunk_overlap,
                )
                await set_progress(30, f"分段完成（策略 {strategy}），共 {len(chunks)} 段，正在向量化…")

                # 向量化
                embedder = await get_active_embedder(session)
                embeddings = await embedder.embed_batch(chunks)
                # v5.12：embedder 回傳數量短少時不可繼續（否則 zip 截斷 → 文件標 READY 但段落/向量缺、無錯）
                if len(embeddings) != len(chunks):
                    raise RuntimeError(
                        f"embed_batch 回傳數量不符：chunks={len(chunks)} embeddings={len(embeddings)}"
                        "（embedder 丟棄過長輸入或回傳部分批次）→ 中止交給 retry，不標 READY"
                    )
                await set_progress(70, "正在寫入段落與向量…")

                # 冪等清理：先刪除舊段落（retry 場景）
                # v5.13: milvus 模式先撈舊段落 id → 刪 PG 後清 Milvus 向量（避免重處理殘留）
                from app.core import milvus_store
                _old_pids: list = []
                if milvus_store.is_enabled():
                    _r = await session.execute(
                        text_sql("SELECT id FROM paragraphs WHERE document_id = :d"), {"d": str(doc.id)}
                    )
                    _old_pids = [str(x[0]) for x in _r.fetchall()]
                await session.execute(delete(Paragraph).where(Paragraph.document_id == doc.id))
                await session.commit()
                await milvus_store.safe_delete_by_paragraphs(_old_pids)

                # 寫入段落與向量（每 50 筆批次提交）
                # workspace_id 從 document 繼承（RFC-001 Stage 2）
                for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                    para = Paragraph(
                        workspace_id=doc.workspace_id,
                        document_id=doc.id,
                        knowledge_base_id=doc.knowledge_base_id,
                        content=chunk,
                        order_index=idx,
                        char_count=len(chunk),
                    )
                    session.add(para)
                    await session.flush()
                    await upsert_embedding(session, para.id, doc.knowledge_base_id, emb)
                    await update_search_vector(session, para.id, chunk)
                    if (idx + 1) % 50 == 0:
                        await session.commit()

                doc.paragraph_count = len(chunks)
                doc.char_count = len(text)
                doc.status = DocStatus.READY
                await set_progress(100, "處理完成")
                await session.commit()
                log.info("document_processed", doc_id=doc_id, paragraphs=len(chunks))

                # RFC-014：KB 開啟 graph_enabled → 背景建圖（不阻塞、失敗不影響 RAG）
                if kb_settings.get("graph_enabled"):
                    try:
                        from app.tasks.build_graph import build_graph
                        build_graph.delay(
                            str(doc.knowledge_base_id), str(doc.workspace_id), str(doc.id)
                        )
                    except Exception as ge:  # noqa: BLE001
                        log.warning("graph_enqueue_failed", doc_id=doc_id, error=str(ge))
                return {"status": "success", "paragraphs": len(chunks)}

            except Exception as exc:
                try:
                    await session.rollback()
                    doc2 = await session.get(Document, uuid.UUID(doc_id))
                    if doc2:
                        doc2.status = DocStatus.ERROR
                        doc2.error_message = str(exc)[:500]
                        doc2.meta = {
                            **(doc2.meta or {}),
                            "progress": 0,
                            "progress_message": f"處理失敗：{str(exc)[:100]}",
                        }
                        await session.commit()
                except Exception:
                    pass
                raise
    finally:
        await engine.dispose()


# ════════════════════════════════════════════════════════════════════════
#  v5.10.x P0-1：段落重新向量化（regen_embedding / KB 匯入後補 embed）
#  段落已存在，只重算 embedding + tsvector；不碰 download / chunking。
# ════════════════════════════════════════════════════════════════════════
@celery_app.task(
    bind=True,
    name="app.tasks.process_document.regen_embeddings",
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
)
def regen_embeddings(self, paragraph_ids: list[str]) -> dict:
    """批次重算指定段落的向量 + 全文索引（段落編輯 / 批次 regen / 匯入補 embed）。"""
    try:
        return asyncio.run(_async_regen(paragraph_ids))
    except Exception as exc:
        countdown = min(30 * (2 ** self.request.retries), 300)
        log.error("regen_embeddings_will_retry", count=len(paragraph_ids), error=str(exc), countdown=countdown)
        raise self.retry(exc=exc, countdown=countdown)


async def _async_regen(paragraph_ids: list[str]) -> dict:
    """對既有段落重算 embedding + tsvector，在 worker 獨立 event loop 執行。"""
    engine = create_async_engine(settings.DB_URL, pool_size=1, max_overflow=0)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            ids = [uuid.UUID(p) for p in paragraph_ids]
            rows = await session.execute(select(Paragraph).where(Paragraph.id.in_(ids)))
            paras: list[Paragraph] = list(rows.scalars().all())
            if not paras:
                log.warning("regen_embeddings_no_rows", requested=len(paragraph_ids))
                return {"status": "success", "regenerated": 0}

            embedder = await get_active_embedder(session)
            embeddings = await embedder.embed_batch([p.content for p in paras])
            # v5.12: 同 inline — 數量不符即丟錯交給 Celery retry，避免靜默漏向量。
            if len(embeddings) != len(paras):
                raise RuntimeError(
                    f"regen embedding 數量不符：{len(embeddings)} != {len(paras)}（疑批次截斷）"
                )
            done = 0
            for p, emb in zip(paras, embeddings):
                await upsert_embedding(session, p.id, p.knowledge_base_id, emb)
                await update_search_vector(session, p.id, p.content)
                done += 1
                if done % 50 == 0:
                    await session.commit()
            await session.commit()
            log.info("regen_embeddings_done", regenerated=done, requested=len(paragraph_ids))
            return {"status": "success", "regenerated": done}
    finally:
        await engine.dispose()


# ── v5.12: 卡住文件處理任務的回收 reaper ─────────────────────────────────────
#   情境：批次上傳一堆檔 → 期間 worker 重啟（部署/crash/OOM）或 redis 中斷 → 佇列裡的
#   process_document 任務遺失（celery redis broker 不保證重投遞）→ 文件永遠卡 pending、
#   客戶以為傳了卻搜不到。失敗的會標 error，但「任務遺失」的停在 pending 沒人管。
#   解法：worker 啟動 + beat 每 5 分鐘掃「卡 pending/processing 過久」的文件 → 重新 enqueue。
_STALE_MINUTES = 15      # status 卡 pending/processing 超過此分鐘數未更新 → 視為任務遺失
_MAX_REAP = 3            # 重排上限；達上限仍卡 → 標 error 放棄（避免無限重排）


@celery_app.task(name="app.tasks.process_document.reap_stuck_documents")
def reap_stuck_documents() -> dict:
    """掃出卡住的文件並重新 enqueue 處理（見上方說明）。"""
    return asyncio.run(_reap_stuck())


async def _reap_stuck() -> dict:
    engine = create_async_engine(settings.DB_URL, pool_size=1, max_overflow=0)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    requeue: list[tuple[str, str, str]] = []
    gave_up = 0
    try:
        async with session_factory() as session:
            rows = await session.execute(text_sql("""
                SELECT id, storage_path, name, COALESCE((meta->>'reap_count')::int, 0) AS rc
                FROM documents
                WHERE status IN ('pending', 'processing')
                  AND storage_path IS NOT NULL
                  AND updated_at < now() - make_interval(mins => :mins)
            """), {"mins": _STALE_MINUTES})
            for r in rows.fetchall():
                if r.rc >= _MAX_REAP:
                    # 重排多次仍卡 → 放棄、標 error（不再無限重排）
                    await session.execute(text_sql("""
                        UPDATE documents SET status = 'error',
                            meta = jsonb_set(COALESCE(meta, '{}'::jsonb), '{progress_message}',
                                   '"處理任務多次遺失、已放棄，請重新上傳"'::jsonb)
                        WHERE id = :id
                    """), {"id": str(r.id)})
                    gave_up += 1
                    continue
                # reap_count++ 並 bump updated_at（避免下一輪 beat 在任務跑起來前又重複回收）
                await session.execute(text_sql("""
                    UPDATE documents SET status = 'pending', updated_at = now(),
                        meta = jsonb_set(COALESCE(meta, '{}'::jsonb), '{reap_count}',
                               to_jsonb(COALESCE((meta->>'reap_count')::int, 0) + 1))
                    WHERE id = :id
                """), {"id": str(r.id)})
                requeue.append((str(r.id), r.storage_path, r.name))
            await session.commit()
    finally:
        await engine.dispose()

    # commit 後再送任務（避免任務先跑完、reap_count/updated_at 還沒落地造成重複回收）
    for doc_id, key, name in requeue:
        celery_app.send_task(
            "app.tasks.process_document.process_document",
            args=[doc_id, key, name], queue="knowledge",
        )
    if requeue or gave_up:
        log.warning("documents_reaped", requeued=len(requeue), gave_up=gave_up)
    return {"requeued": len(requeue), "gave_up": gave_up}
