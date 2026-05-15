"""段落管理 API"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import Paragraph
from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session

router = APIRouter()


class ParagraphUpdate(BaseModel):
    content: str | None = None
    title: str | None = None
    is_active: bool | None = None


@router.get("/{doc_id}", response_model=ApiResponse)
async def list_paragraphs(doc_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Paragraph).where(Paragraph.document_id == doc_id).order_by(Paragraph.order_index)
    )
    paragraphs = result.scalars().all()
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
    session: AsyncSession = Depends(get_session),
):
    p = await session.get(Paragraph, paragraph_id)
    if not p:
        raise HTTPException(status_code=404, detail="段落不存在")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(p, field, value)
    if body.content:
        p.char_count = len(body.content)
    return ApiResponse(message="段落已更新")


@router.delete("/{paragraph_id}", response_model=ApiResponse)
async def delete_paragraph(paragraph_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    p = await session.get(Paragraph, paragraph_id)
    if not p:
        raise HTTPException(status_code=404, detail="段落不存在")
    await session.delete(p)
    return ApiResponse(message="段落已刪除")
