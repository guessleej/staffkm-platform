"""Workflow KB inline-write API（RFC-013 第二階段）。

供 agent service 的 kb_writer workflow node 呼叫；
寫入後立刻 chunk（依 KB 的 chunk_strategy）並 schedule embedding。

特點：
- 純文字寫入，不入 minio
- upsert_key：同 workflow + 同 key 命中時，先刪舊 Document（含 paragraphs / embeddings cascade）
- enforce KB 必須為 source_type='workflow'，避免污染手動 KB
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import (
    Document, DocStatus, KnowledgeBase, Paragraph,
)
from app.tasks.process_document import process_document
from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import (
    TenantContext, WorkspaceScopedQuery, require_writer,
)

router = APIRouter()


class InlineWriteReq(BaseModel):
    content:     str = Field(..., min_length=1, max_length=100_000)
    title:       str | None = None
    source:      str | None = None
    chunking:    Literal["single", "auto", "paragraph"] = "single"
    upsert_key:  str | None = Field(default=None, max_length=128)


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


@router.post("/{kb_id}/inline-write", response_model=ApiResponse)
async def inline_write(
    kb_id: uuid.UUID,
    body: InlineWriteReq,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    """為 workflow KB 寫入純文字段落；非 workflow KB 拒絕。"""
    # 1. 驗證 KB 屬於 workspace 且為 workflow 型
    q = WorkspaceScopedQuery(KnowledgeBase).select().where(KnowledgeBase.id == kb_id)
    kb = (await session.execute(q)).scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="知識庫不存在或不屬於此工作區")
    r = await session.execute(
        text("SELECT source_type, source_workflow_id FROM knowledge_bases WHERE id = :id"),
        {"id": str(kb_id)},
    )
    row = r.fetchone()
    src_type = (row._mapping.get("source_type") if row else "manual") or "manual"
    if src_type != "workflow":
        raise HTTPException(
            status_code=400,
            detail="此 KB 並非 workflow 型；請先 POST /convert-to-workflow 或選別的 KB",
        )

    # 2. upsert_key：先刪同 key 舊 Document
    if body.upsert_key:
        old_rows = await session.execute(
            text(
                "SELECT id FROM documents "
                "WHERE knowledge_base_id = :kb AND workspace_id = :ws "
                "AND meta->>'upsert_key' = :uk"
            ),
            {"kb": str(kb_id), "ws": str(ctx.workspace_id), "uk": body.upsert_key},
        )
        old_ids = [r._mapping["id"] for r in old_rows.fetchall()]
        if old_ids:
            # paragraphs / embeddings 隨 cascade 刪
            await session.execute(
                text("DELETE FROM documents WHERE id = ANY(:ids)"),
                {"ids": old_ids},
            )

    # 3. 建 Document
    title = (body.title or body.upsert_key or
             f"inline-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{_content_hash(body.content)}")
    doc = Document(
        workspace_id=ctx.workspace_id,
        knowledge_base_id=kb_id,
        name=title[:256],
        file_type="inline",
        file_size=len(body.content.encode("utf-8")),
        status=DocStatus.PROCESSING,
        paragraph_count=0,
        char_count=len(body.content),
        meta={
            "source":     body.source or "",
            "upsert_key": body.upsert_key or "",
            "chunking":   body.chunking,
            "inline":     True,
        },
    )
    session.add(doc)
    await session.flush()

    # 4. 切片寫入 paragraphs
    chunks = _chunk(body.content, kb=kb, mode=body.chunking)
    paragraphs: list[Paragraph] = []
    for idx, chunk_text in enumerate(chunks):
        p = Paragraph(
            workspace_id=ctx.workspace_id,
            document_id=doc.id,
            knowledge_base_id=kb_id,
            content=chunk_text,
            title=body.title,
            order_index=idx,
            char_count=len(chunk_text),
            meta={"source": body.source or "", "inline": True},
        )
        session.add(p)
        paragraphs.append(p)

    doc.paragraph_count = len(paragraphs)
    doc.status = DocStatus.PENDING  # embedding pending；可由 worker 處理
    await session.commit()

    # 5. 觸發 embedding 背景任務（沿用既有 process_document，但走 inline-mode 跳過 minio download）
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
        # 任務派發失敗不致命；下次手動觸發即可
        pass

    return ApiResponse(message=f"已寫入 {len(paragraphs)} 個段落", data={
        "document_id": str(doc.id),
        "paragraphs":  len(paragraphs),
        "task_id":     task_id,
    })


def _chunk(content: str, *, kb: KnowledgeBase, mode: str) -> list[str]:
    """簡化版切片：以 KB 設定 chunk_size 為上限。"""
    text_in = content.strip()
    if not text_in:
        return []
    if mode == "single":
        return [text_in]
    if mode == "paragraph":
        return [p.strip() for p in text_in.split("\n\n") if p.strip()]
    # mode == "auto" → 依 KB.chunk_size 滑動切片（簡化版，無 overlap）
    size = max(64, getattr(kb, "chunk_size", 512))
    return [text_in[i:i + size] for i in range(0, len(text_in), size)]
