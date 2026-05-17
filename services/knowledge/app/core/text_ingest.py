"""Sprint 16 — 純文字 → KB 入庫的可重用 helper。

抽出自 inline_write API；供 web_sync task / 未來其他「文字直入」場景共用。
不依賴 FastAPI / TenantContext，需要 caller 自己提供 session + workspace_id。
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime

from sqlalchemy import text as text_sql
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import Document, DocStatus, KnowledgeBase, Paragraph


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _chunk(content: str, *, kb: KnowledgeBase, mode: str) -> list[str]:
    """簡化版切片；與 inline_write 一致。"""
    text_in = content.strip()
    if not text_in:
        return []
    if mode == "single":
        return [text_in]
    if mode == "paragraph":
        return [p.strip() for p in text_in.split("\n\n") if p.strip()]
    size = max(64, getattr(kb, "chunk_size", 512))
    return [text_in[i:i + size] for i in range(0, len(text_in), size)]


async def ingest_text_into_kb(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    kb: KnowledgeBase,
    content: str,
    title: str | None = None,
    source: str | None = None,
    chunking: str = "auto",
    extra_meta: dict | None = None,
    upsert_key: str | None = None,
) -> dict:
    """寫入單份 inline 文件 + 切段，再 schedule embedding。

    `upsert_key`：同 KB 內若已有 meta->>'upsert_key' = 該值的 Document，
    先刪掉再寫新的（用於 web sync 對同一 URL 重抓不要建多份）。

    回傳 {document_id, paragraphs, task_id}。
    """
    # 0. upsert：刪舊
    if upsert_key:
        old_rows = await session.execute(
            text_sql(
                "SELECT id FROM documents "
                "WHERE knowledge_base_id = :kb AND workspace_id = :ws "
                "AND meta->>'upsert_key' = :uk"
            ),
            {"kb": str(kb.id), "ws": str(workspace_id), "uk": upsert_key},
        )
        old_ids = [r._mapping["id"] for r in old_rows.fetchall()]
        if old_ids:
            await session.execute(
                text_sql("DELETE FROM documents WHERE id = ANY(:ids)"),
                {"ids": old_ids},
            )
            await session.flush()

    # 1. Document 落地
    name = (title or f"web-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{_content_hash(content)}")[:256]
    doc = Document(
        workspace_id=workspace_id,
        knowledge_base_id=kb.id,
        name=name,
        file_type="inline",
        file_size=len(content.encode("utf-8")),
        status=DocStatus.PROCESSING,
        paragraph_count=0,
        char_count=len(content),
        meta={
            "source":     source or "",
            "chunking":   chunking,
            "inline":     True,
            "upsert_key": upsert_key or "",
            **(extra_meta or {}),
        },
    )
    session.add(doc)
    await session.flush()

    # 2. 切段
    chunks = _chunk(content, kb=kb, mode=chunking)
    for idx, chunk_text in enumerate(chunks):
        session.add(Paragraph(
            workspace_id=workspace_id,
            document_id=doc.id,
            knowledge_base_id=kb.id,
            content=chunk_text,
            title=title,
            order_index=idx,
            char_count=len(chunk_text),
            meta={"source": source or "", "inline": True},
        ))
    doc.paragraph_count = len(chunks)
    doc.status = DocStatus.PENDING
    await session.commit()

    # 3. schedule embedding（沿用既有 process_document inline-mode）
    from app.tasks.process_document import process_document
    task_id: str | None = None
    try:
        task = process_document.apply_async(
            args=[str(doc.id), None, doc.name],
            kwargs={"inline": True},
            countdown=1,
        )
        task_id = task.id
        doc.meta = {**(doc.meta or {}), "celery_task_id": task_id}
        await session.commit()
    except Exception:
        pass  # 派發失敗不致命

    return {
        "document_id": str(doc.id),
        "paragraphs":  len(chunks),
        "task_id":     task_id,
    }
