"""知識庫 CRUD API（RFC-001 Stage 2 — workspace-scoped）"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import KnowledgeBase, KBStatus
from staffkm_core.schemas.response import ApiResponse, PageMeta, PagedResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import (
    TenantContext, WorkspaceScopedQuery,
    require_member, require_writer, require_admin,
)

router = APIRouter()


class KBCreate(BaseModel):
    name: str
    description: str | None = None
    embedding_model: str = "bge-m3"
    is_public: bool = False


class KBUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_public: bool | None = None


class KBOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    status: str
    embedding_model: str
    is_public: bool
    document_count: int = 0

    model_config = {"from_attributes": True}


@router.get("", response_model=PagedResponse[KBOut])
async def list_knowledge_bases(
    page: int = 1,
    page_size: int = 20,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    offset = (page - 1) * page_size
    q = WorkspaceScopedQuery(KnowledgeBase).select().offset(offset).limit(page_size)
    result = await session.execute(q)
    kbs = result.scalars().all()

    count_q = select(func.count()).select_from(KnowledgeBase).where(
        KnowledgeBase.workspace_id == ctx.workspace_id
    )
    total = await session.scalar(count_q) or 0
    return PagedResponse(
        data=[KBOut.model_validate(kb) for kb in kbs],
        meta=PageMeta(page=page, page_size=page_size, total=total, total_pages=-(-total // page_size)),
    )


@router.post("", response_model=ApiResponse[KBOut], status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    body: KBCreate,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    kb = KnowledgeBase(workspace_id=ctx.workspace_id, **body.model_dump())
    session.add(kb)
    await session.flush()
    return ApiResponse(data=KBOut.model_validate(kb), message="知識庫建立成功")


@router.get("/{kb_id}", response_model=ApiResponse[KBOut])
async def get_knowledge_base(
    kb_id: uuid.UUID,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    q = WorkspaceScopedQuery(KnowledgeBase).select().where(KnowledgeBase.id == kb_id)
    kb = (await session.execute(q)).scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="知識庫不存在或不屬於此工作區")
    return ApiResponse(data=KBOut.model_validate(kb))


@router.patch("/{kb_id}", response_model=ApiResponse[KBOut])
async def update_knowledge_base(
    kb_id: uuid.UUID,
    body: KBUpdate,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    q = WorkspaceScopedQuery(KnowledgeBase).select().where(KnowledgeBase.id == kb_id)
    kb = (await session.execute(q)).scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="知識庫不存在或不屬於此工作區")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(kb, field, value)
    return ApiResponse(data=KBOut.model_validate(kb), message="知識庫更新成功")


@router.delete("/{kb_id}", response_model=ApiResponse)
async def delete_knowledge_base(
    kb_id: uuid.UUID,
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    q = WorkspaceScopedQuery(KnowledgeBase).select().where(KnowledgeBase.id == kb_id)
    kb = (await session.execute(q)).scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="知識庫不存在或不屬於此工作區")
    await session.delete(kb)
    return ApiResponse(message="知識庫已刪除")
