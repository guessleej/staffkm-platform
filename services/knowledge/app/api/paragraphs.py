"""段落管理 API（RFC-001 Stage 2 — workspace-scoped）"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import Document, Paragraph
from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import (
    TenantContext, WorkspaceScopedQuery,
    require_admin, require_member, require_writer,
)

router = APIRouter()


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

    # 段落本身也帶 workspace_id（從 process_document 寫入時帶入）
    q = (
        WorkspaceScopedQuery(Paragraph).select()
        .where(Paragraph.document_id == doc_id)
        .order_by(Paragraph.order_index)
    )
    paragraphs = (await session.execute(q)).scalars().all()
    return ApiResponse(data=[
        {
            "id": str(p.id), "content": p.content, "title": p.title,
            "order_index": p.order_index, "char_count": p.char_count, "is_active": p.is_active,
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
