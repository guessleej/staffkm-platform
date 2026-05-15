"""Celery 背景任務：文件解析 → 分段 → 向量化 → 入庫"""
import asyncio
import io
import uuid
import structlog
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import settings
from app.core.document_processor import DocumentProcessor, TextSplitter
from app.core.embedder import get_embedder
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
def process_document(self, doc_id: str, minio_key: str, filename: str) -> dict:
    """Celery 同步入口，包裝 asyncio 管線。"""
    try:
        return asyncio.run(_async_process(doc_id, minio_key, filename))
    except Exception as exc:
        countdown = min(30 * (2 ** self.request.retries), 300)
        log.error("process_document_will_retry", doc_id=doc_id, error=str(exc), countdown=countdown)
        raise self.retry(exc=exc, countdown=countdown)


async def _async_process(doc_id: str, minio_key: str, filename: str) -> dict:
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
                await set_progress(10, "正在讀取檔案…")

                # 從 MinIO 下載（同步 I/O → 移至執行緒以免卡住 event loop）
                file_bytes = await asyncio.to_thread(download_document, minio_key)

                # 解析文件
                await set_progress(20, "正在解析文件內容…")
                processor = DocumentProcessor()
                text = processor.load(io.BytesIO(file_bytes), filename)

                # 分段
                splitter = TextSplitter(
                    chunk_size=settings.CHUNK_SIZE,
                    chunk_overlap=settings.CHUNK_OVERLAP,
                )
                chunks = splitter.split(text)
                log.info("document_chunked", doc_id=doc_id, chunks=len(chunks))
                await set_progress(30, f"分段完成，共 {len(chunks)} 段，正在向量化…")

                # 向量化
                embedder = get_embedder(
                    settings.EMBEDDING_MODEL,
                    settings.OPENAI_API_KEY,
                    settings.EMBEDDING_BASE_URL or None,
                )
                embeddings = await embedder.embed_batch(chunks)
                await set_progress(70, "正在寫入段落與向量…")

                # 冪等清理：先刪除舊段落（retry 場景）
                await session.execute(delete(Paragraph).where(Paragraph.document_id == doc.id))
                await session.commit()

                # 寫入段落與向量（每 50 筆批次提交）
                for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                    para = Paragraph(
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
                log.info("document_processed", doc_id=doc_id, paragraphs=len(chunks))
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
