"""段落管理 API（RFC-001 Stage 2 — workspace-scoped）"""
import uuid
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import Document, Paragraph
from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import (
    TenantContext, WorkspaceScopedQuery,
    require_admin, require_member, require_writer,
)

log = logging.getLogger(__name__)
router = APIRouter()


async def _embed_and_index(
    session: AsyncSession,
    paragraph_id: uuid.UUID,
    kb_id: uuid.UUID,
    content: str,
) -> bool:
    """為單一段落算 embedding + tsvector；失敗回 False（不 raise）。"""
    from app.config import settings
    from app.core.embedder import get_embedder
    from app.core.vectorstore import upsert_embedding, update_search_vector
    try:
        await update_search_vector(session, paragraph_id, content)
        embedder = get_embedder(
            settings.EMBEDDING_MODEL,
            settings.OPENAI_API_KEY,
            settings.EMBEDDING_BASE_URL or None,
        )
        vec = (await embedder.embed_batch([content]))[0]
        await upsert_embedding(session, paragraph_id, kb_id, vec)
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("embed paragraph %s failed: %s", paragraph_id, exc)
        return False


class ParagraphUpdate(BaseModel):
    content:   str | None  = None
    title:     str | None  = None
    is_active: bool | None = None


@router.get("/{doc_id}", response_model=ApiResponse)
async def list_paragraphs(
    doc_id: uuid.UUID,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    # 確認 doc 屬於當前 workspace
    doc_q = WorkspaceScopedQuery(Document).select().where(Document.id == doc_id)
    doc = (await session.execute(doc_q)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在或不屬於此工作區")

    # v2.1 11-4：白名單 ACL
    from app.core.kb_acl import enforce_kb_access
    await enforce_kb_access(ctx, doc.knowledge_base_id, session, need="read")

    # 段落本身也帶 workspace_id（從 process_document 寫入時帶入）
    q = (
        WorkspaceScopedQuery(Paragraph).select()
        .where(Paragraph.document_id == doc_id)
        .order_by(Paragraph.order_index)
    )
    paragraphs = (await session.execute(q)).scalars().all()

    # 查 has_embedding（一次查全 doc，避免 N+1）
    embedded_ids: set[str] = set()
    if paragraphs:
        rows = await session.execute(
            text(
                "SELECT paragraph_id::text FROM paragraph_embeddings "
                "WHERE paragraph_id = ANY(CAST(:ids AS uuid[]))"
            ),
            {"ids": "{" + ",".join(str(p.id) for p in paragraphs) + "}"},
        )
        embedded_ids = {r[0] for r in rows.fetchall()}

    return ApiResponse(data=[
        {
            "id": str(p.id), "content": p.content, "title": p.title,
            "order_index": p.order_index, "char_count": p.char_count,
            "is_active": p.is_active, "qa_pairs": p.qa_pairs or [],
            "has_embedding": str(p.id) in embedded_ids,
        }
        for p in paragraphs
    ])


@router.patch("/{paragraph_id}", response_model=ApiResponse)
async def update_paragraph(
    paragraph_id: uuid.UUID,
    body: ParagraphUpdate,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    q = WorkspaceScopedQuery(Paragraph).select().where(Paragraph.id == paragraph_id)
    p = (await session.execute(q)).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="段落不存在或不屬於此工作區")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(p, field, value)
    if body.content:
        p.char_count = len(body.content)
    return ApiResponse(message="段落已更新")


@router.delete("/{paragraph_id}", response_model=ApiResponse)
async def delete_paragraph(
    paragraph_id: uuid.UUID,
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    q = WorkspaceScopedQuery(Paragraph).select().where(Paragraph.id == paragraph_id)
    p = (await session.execute(q)).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="段落不存在或不屬於此工作區")
    await session.delete(p)
    return ApiResponse(message="段落已刪除")


# ═══════════════════════════════════════════════════════════════════════
#  Round 10-2：段落層級 Q&A 生成 / 編輯
# ═══════════════════════════════════════════════════════════════════════
from pydantic import BaseModel, Field
from typing import Literal


class QAGenerateReq(BaseModel):
    n: int = Field(default=3, ge=1, le=10)
    model: str | None = None
    append: bool = False  # True = 加到既有；False = 覆蓋


class QAItem(BaseModel):
    question: str = Field(..., min_length=1, max_length=512)
    answer:   str = Field(..., min_length=1, max_length=2048)
    source:   Literal["auto", "manual"] = "manual"


class QAReplaceReq(BaseModel):
    qa: list[QAItem]


@router.post("/{paragraph_id}/generate-qa", response_model=ApiResponse)
async def generate_qa(
    paragraph_id: uuid.UUID,
    body: QAGenerateReq,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    """對指定段落呼叫 LLM 產生 Q&A pairs。"""
    from app.core.qa_generator import generate_qa_for_text

    q = WorkspaceScopedQuery(Paragraph).select().where(Paragraph.id == paragraph_id)
    p = (await session.execute(q)).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="段落不存在或不屬於此工作區")

    try:
        new_pairs = await generate_qa_for_text(p.content, n=body.n, model=body.model)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    if body.append:
        existing = list(p.qa_pairs or [])
        existing.extend(new_pairs)
        p.qa_pairs = existing
    else:
        p.qa_pairs = new_pairs
    await session.commit()
    return ApiResponse(message=f"已產生 {len(new_pairs)} 組 Q&A", data={
        "qa_pairs": p.qa_pairs,
    })


@router.get("/{paragraph_id}/qa", response_model=ApiResponse)
async def list_qa(
    paragraph_id: uuid.UUID,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    q = WorkspaceScopedQuery(Paragraph).select().where(Paragraph.id == paragraph_id)
    p = (await session.execute(q)).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="段落不存在或不屬於此工作區")
    return ApiResponse(data=p.qa_pairs or [])


@router.put("/{paragraph_id}/qa", response_model=ApiResponse)
async def replace_qa(
    paragraph_id: uuid.UUID,
    body: QAReplaceReq,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    """整批替換段落的 qa_pairs（包含手動編輯 / 刪除單筆後 PUT 回來）。"""
    q = WorkspaceScopedQuery(Paragraph).select().where(Paragraph.id == paragraph_id)
    p = (await session.execute(q)).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="段落不存在或不屬於此工作區")
    p.qa_pairs = [pair.model_dump() for pair in body.qa]
    await session.commit()
    return ApiResponse(message="qa_pairs 已更新", data={"count": len(p.qa_pairs)})


# ═══════════════════════════════════════════════════════════════════════
#  v2.1 11-3：段落排序（拖移上下 / 移到頂 / 移到底）
# ═══════════════════════════════════════════════════════════════════════
class ReorderReq(BaseModel):
    """以新的 order 順序 PUT 整個 document 的段落 ID 序列。"""
    ordered_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=2000)


@router.put("/doc/{doc_id}/reorder", response_model=ApiResponse)
async def reorder_paragraphs(
    doc_id: uuid.UUID,
    body: ReorderReq,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    """整批更新段落 order_index。

    - ordered_ids 必須涵蓋 document 內所有段落
    - 任一 id 不屬於 document → 400
    - 一次 transaction 內完成 N 次 UPDATE
    """
    # 驗證 doc 屬於 workspace
    doc_q = WorkspaceScopedQuery(Document).select().where(Document.id == doc_id)
    doc = (await session.execute(doc_q)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在或不屬於此工作區")

    # 取目前段落 id set
    existing_q = (
        WorkspaceScopedQuery(Paragraph).select()
        .where(Paragraph.document_id == doc_id)
    )
    existing = list((await session.execute(existing_q)).scalars().all())
    existing_ids = {p.id for p in existing}
    sent_ids = set(body.ordered_ids)

    if sent_ids != existing_ids:
        raise HTTPException(
            status_code=400,
            detail=(
                "ordered_ids 必須與 document 內所有段落一致 "
                f"（傳入 {len(sent_ids)}，現有 {len(existing_ids)}）"
            ),
        )

    # 索引映射
    id_to_pos = {pid: i for i, pid in enumerate(body.ordered_ids)}
    for p in existing:
        p.order_index = id_to_pos[p.id]
    await session.commit()
    return ApiResponse(message="段落順序已更新", data={"count": len(existing)})


@router.post("/{paragraph_id}/move", response_model=ApiResponse)
async def move_paragraph(
    paragraph_id: uuid.UUID,
    direction: str,    # "up" | "down" | "top" | "bottom"
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    """單筆段落上下移動 / 移到頂 / 底；自動重排同 document 內其餘段落 order_index。"""
    if direction not in ("up", "down", "top", "bottom"):
        raise HTTPException(status_code=400, detail="direction 必須為 up|down|top|bottom")

    q = WorkspaceScopedQuery(Paragraph).select().where(Paragraph.id == paragraph_id)
    p = (await session.execute(q)).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="段落不存在或不屬於此工作區")

    siblings_q = (
        WorkspaceScopedQuery(Paragraph).select()
        .where(Paragraph.document_id == p.document_id)
        .order_by(Paragraph.order_index)
    )
    siblings = list((await session.execute(siblings_q)).scalars().all())
    if len(siblings) <= 1:
        return ApiResponse(message="僅一段，無需移動")

    cur_idx = next((i for i, s in enumerate(siblings) if s.id == p.id), None)
    if cur_idx is None:
        raise HTTPException(status_code=500, detail="找不到當前段落於文件中")

    new_idx = cur_idx
    if direction == "up" and cur_idx > 0:
        new_idx = cur_idx - 1
    elif direction == "down" and cur_idx < len(siblings) - 1:
        new_idx = cur_idx + 1
    elif direction == "top":
        new_idx = 0
    elif direction == "bottom":
        new_idx = len(siblings) - 1

    if new_idx == cur_idx:
        return ApiResponse(message="已在邊界，未變動")

    moved = siblings.pop(cur_idx)
    siblings.insert(new_idx, moved)
    for i, s in enumerate(siblings):
        s.order_index = i
    await session.commit()
    return ApiResponse(message="移動完成", data={
        "from_index": cur_idx, "to_index": new_idx,
    })


# ═══════════════════════════════════════════════════════════════════════
#  v5.x：MaxKB parity — add / toggle / split / merge / bulk / hit-test
# ═══════════════════════════════════════════════════════════════════════
class ParagraphAddReq(BaseModel):
    content:     str  = Field(..., min_length=1, max_length=20000)
    title:       str | None = Field(default=None, max_length=256)
    order_index: int | None = None


@router.post("/doc/{doc_id}/add", response_model=ApiResponse)
async def add_paragraph(
    doc_id: uuid.UUID,
    body: ParagraphAddReq,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    """手動新增段落 — 立刻算 embedding + tsvector。"""
    doc_q = WorkspaceScopedQuery(Document).select().where(Document.id == doc_id)
    doc = (await session.execute(doc_q)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在或不屬於此工作區")

    # 算 order_index：未提供則放最後
    if body.order_index is None:
        max_row = await session.execute(
            text("SELECT COALESCE(MAX(order_index), -1) FROM paragraphs WHERE document_id = :did"),
            {"did": str(doc_id)},
        )
        body.order_index = int(max_row.scalar() or -1) + 1

    p = Paragraph(
        workspace_id=ctx.workspace_id,
        document_id=doc_id,
        knowledge_base_id=doc.knowledge_base_id,
        content=body.content,
        title=body.title,
        order_index=body.order_index,
        char_count=len(body.content),
        is_active=True,
        qa_pairs=[],
    )
    session.add(p)
    await session.flush()

    ok = await _embed_and_index(session, p.id, doc.knowledge_base_id, body.content)
    await session.commit()
    return ApiResponse(message="段落已新增", data={
        "id": str(p.id), "order_index": p.order_index,
        "char_count": p.char_count, "has_embedding": ok,
    })


@router.patch("/{paragraph_id}/toggle", response_model=ApiResponse)
async def toggle_paragraph(
    paragraph_id: uuid.UUID,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    """切換 is_active；不重算 embedding。"""
    q = WorkspaceScopedQuery(Paragraph).select().where(Paragraph.id == paragraph_id)
    p = (await session.execute(q)).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="段落不存在或不屬於此工作區")
    p.is_active = not p.is_active
    await session.commit()
    return ApiResponse(message="已切換啟用狀態", data={"is_active": p.is_active})


class ParagraphSplitReq(BaseModel):
    separator: str | None = Field(default="\n\n", max_length=64)
    positions: list[int] | None = Field(default=None, description="char offsets，遞增")


@router.post("/{paragraph_id}/split", response_model=ApiResponse)
async def split_paragraph(
    paragraph_id: uuid.UUID,
    body: ParagraphSplitReq,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    """拆段：用 positions（字元 offset）或 separator。原段變第一段，後面 INSERT 新段。"""
    q = WorkspaceScopedQuery(Paragraph).select().where(Paragraph.id == paragraph_id)
    p = (await session.execute(q)).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="段落不存在或不屬於此工作區")

    content = p.content
    pieces: list[str] = []
    if body.positions:
        offsets = sorted({int(x) for x in body.positions if 0 < int(x) < len(content)})
        if not offsets:
            raise HTTPException(status_code=400, detail="positions 無有效位置")
        prev = 0
        for off in offsets:
            pieces.append(content[prev:off])
            prev = off
        pieces.append(content[prev:])
    else:
        sep = body.separator or "\n\n"
        pieces = [s for s in content.split(sep) if s.strip()]

    pieces = [s.strip() for s in pieces if s.strip()]
    if len(pieces) < 2:
        raise HTTPException(status_code=400, detail="切分後不足 2 段；請改 separator 或 positions")

    # 第一段：覆寫原 paragraph
    p.content = pieces[0]
    p.char_count = len(pieces[0])
    # 清掉舊向量（會由新算覆蓋）
    await session.execute(
        text("DELETE FROM paragraph_embeddings WHERE paragraph_id = :pid"),
        {"pid": str(p.id)},
    )

    # 為了在中間插入，將後續同 doc 的 order_index 往後推
    insert_count = len(pieces) - 1
    await session.execute(
        text(
            "UPDATE paragraphs SET order_index = order_index + :n "
            "WHERE document_id = :did AND order_index > :base"
        ),
        {"n": insert_count, "did": str(p.document_id), "base": p.order_index},
    )

    new_ids: list[uuid.UUID] = []
    for i, chunk in enumerate(pieces[1:], start=1):
        np = Paragraph(
            workspace_id=p.workspace_id,
            document_id=p.document_id,
            knowledge_base_id=p.knowledge_base_id,
            content=chunk,
            title=p.title,
            order_index=p.order_index + i,
            char_count=len(chunk),
            is_active=p.is_active,
            qa_pairs=[],
        )
        session.add(np)
        new_ids.append(np.id)  # type: ignore[arg-type]
    await session.flush()

    # 重算第一段 + 新段的 embedding
    await _embed_and_index(session, p.id, p.knowledge_base_id, p.content)
    for npid, chunk in zip(new_ids, pieces[1:]):
        await _embed_and_index(session, npid, p.knowledge_base_id, chunk)

    await session.commit()
    return ApiResponse(message=f"已拆為 {len(pieces)} 段", data={
        "count": len(pieces),
        "new_paragraph_ids": [str(x) for x in new_ids],
    })


class ParagraphMergeReq(BaseModel):
    paragraph_ids: list[uuid.UUID] = Field(..., min_length=2, max_length=50)


@router.post("/merge", response_model=ApiResponse)
async def merge_paragraphs(
    body: ParagraphMergeReq,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    """把多個段落合併為第一個；其餘刪除。必須同 document。"""
    q = (
        WorkspaceScopedQuery(Paragraph).select()
        .where(Paragraph.id.in_(body.paragraph_ids))
    )
    rows = list((await session.execute(q)).scalars().all())
    if len(rows) != len(body.paragraph_ids):
        raise HTTPException(status_code=404, detail="部分段落不存在或不屬於此工作區")
    doc_ids = {r.document_id for r in rows}
    if len(doc_ids) != 1:
        raise HTTPException(status_code=400, detail="合併段落必須屬於同一文件")

    # 維持使用者送來的順序
    by_id = {r.id: r for r in rows}
    ordered = [by_id[pid] for pid in body.paragraph_ids]
    first = ordered[0]
    merged = "\n\n".join(r.content for r in ordered)
    first.content = merged
    first.char_count = len(merged)
    # 第一段以外刪掉（CASCADE 會清 paragraph_embeddings）
    for r in ordered[1:]:
        await session.delete(r)
    await session.flush()
    # 重算第一段向量
    await session.execute(
        text("DELETE FROM paragraph_embeddings WHERE paragraph_id = :pid"),
        {"pid": str(first.id)},
    )
    await _embed_and_index(session, first.id, first.knowledge_base_id, first.content)
    await session.commit()
    return ApiResponse(message=f"已合併 {len(ordered)} 段", data={
        "paragraph_id": str(first.id),
        "char_count": first.char_count,
    })


class ParagraphBulkReq(BaseModel):
    action:        Literal["delete", "enable", "disable", "regen_embedding"]
    paragraph_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=500)


@router.post("/bulk", response_model=ApiResponse)
async def bulk_paragraph_action(
    body: ParagraphBulkReq,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    """批次：delete / enable / disable / regen_embedding。"""
    q = (
        WorkspaceScopedQuery(Paragraph).select()
        .where(Paragraph.id.in_(body.paragraph_ids))
    )
    rows = list((await session.execute(q)).scalars().all())
    if not rows:
        raise HTTPException(status_code=404, detail="找不到任何段落")

    if body.action == "delete":
        for r in rows:
            await session.delete(r)
        await session.commit()
        return ApiResponse(message=f"已刪除 {len(rows)} 段", data={"affected": len(rows)})

    if body.action in ("enable", "disable"):
        new_val = body.action == "enable"
        for r in rows:
            r.is_active = new_val
        await session.commit()
        return ApiResponse(
            message=f"已{'啟用' if new_val else '停用'} {len(rows)} 段",
            data={"affected": len(rows), "is_active": new_val},
        )

    # regen_embedding：太重，先回 queued placeholder（TODO v5.1 接 celery）
    log.warning("bulk regen_embedding queued (not yet wired to celery): %d ids", len(rows))
    return ApiResponse(
        message=f"已排程 {len(rows)} 段重建向量（背景處理中）",
        data={"queued": len(rows)},
    )


class ParagraphHitTestReq(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)


@router.post("/{paragraph_id}/hit-test", response_model=ApiResponse)
async def hit_test_paragraph(
    paragraph_id: uuid.UUID,
    body: ParagraphHitTestReq,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    """單段命中測試 — 算 query 與此段 embedding 的 cosine similarity。"""
    from app.config import settings
    from app.core.embedder import get_embedder

    q = WorkspaceScopedQuery(Paragraph).select().where(Paragraph.id == paragraph_id)
    p = (await session.execute(q)).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="段落不存在或不屬於此工作區")

    embedder = get_embedder(
        settings.EMBEDDING_MODEL,
        settings.OPENAI_API_KEY,
        settings.EMBEDDING_BASE_URL or None,
    )
    qvec = await embedder.embed_query(body.query)

    row = await session.execute(
        text(
            "SELECT 1 - (embedding <=> CAST(:qv AS vector)) AS score "
            "FROM paragraph_embeddings WHERE paragraph_id = :pid"
        ),
        {"qv": str(qvec), "pid": str(paragraph_id)},
    )
    rec = row.first()
    if not rec:
        return ApiResponse(message="該段落尚未向量化", data={
            "score": None, "has_embedding": False, "query": body.query,
        })
    return ApiResponse(data={
        "score": round(float(rec[0]), 6),
        "has_embedding": True,
        "query": body.query,
        "paragraph_id": str(paragraph_id),
    })
