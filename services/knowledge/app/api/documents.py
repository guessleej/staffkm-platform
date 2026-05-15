"""文件上傳與管理 API（RFC-001 Stage 2 — workspace-scoped）"""
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.storage import delete_document, upload_document
from app.models.knowledge_base import Document, DocStatus, KnowledgeBase
from app.tasks.process_document import process_document
from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import (
    TenantContext, WorkspaceScopedQuery,
    require_admin, require_member, require_writer,
)

router = APIRouter()


async def _verify_kb_in_workspace(
    kb_id: uuid.UUID, ctx: TenantContext, session: AsyncSession,
) -> KnowledgeBase:
    """確認 kb 屬於當前 workspace；否則 404。"""
    q = WorkspaceScopedQuery(KnowledgeBase).select().where(KnowledgeBase.id == kb_id)
    kb = (await session.execute(q)).scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="知識庫不存在或不屬於此工作區")
    return kb


@router.post("/{kb_id}/upload", response_model=ApiResponse)
async def upload_document_api(
    kb_id: uuid.UUID,
    file: UploadFile = File(...),
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    await _verify_kb_in_workspace(kb_id, ctx, session)

    ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支援的檔案格式：{ext}")

    contents = await file.read()
    if len(contents) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"檔案超過 {settings.MAX_FILE_SIZE_MB}MB 限制")

    doc = Document(
        workspace_id=ctx.workspace_id,
        knowledge_base_id=kb_id,
        name=file.filename,
        file_type=ext.lstrip("."),
        file_size=len(contents),
        status=DocStatus.PENDING,
    )
    session.add(doc)
    await session.flush()

    minio_key = f"documents/{doc.id}/{file.filename}"
    try:
        upload_document(contents, minio_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"檔案儲存失敗：{e}")

    doc.storage_path = minio_key
    doc.meta = {"progress": 0, "progress_message": "等待處理…"}
    await session.commit()

    task = process_document.apply_async(
        args=[str(doc.id), minio_key, file.filename],
        countdown=1,
    )
    doc.meta = {**doc.meta, "celery_task_id": task.id}
    await session.commit()

    return ApiResponse(
        data={"document_id": str(doc.id), "task_id": task.id},
        message="文件上傳成功，正在背景處理中",
    )


@router.get("/{kb_id}", response_model=ApiResponse)
async def list_documents(
    kb_id: uuid.UUID,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    await _verify_kb_in_workspace(kb_id, ctx, session)
    q = (
        WorkspaceScopedQuery(Document).select()
        .where(Document.knowledge_base_id == kb_id)
    )
    docs = (await session.execute(q)).scalars().all()
    return ApiResponse(data=[
        {
            "id": str(d.id),
            "name": d.name,
            "status": d.status,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "paragraph_count": d.paragraph_count,
            "char_count": d.char_count,
            "progress": (d.meta or {}).get("progress", 0),
            "progress_message": (d.meta or {}).get("progress_message", ""),
            "task_id": (d.meta or {}).get("celery_task_id"),
            "error_message": d.error_message,
        }
        for d in docs
    ])


@router.delete("/{doc_id}", response_model=ApiResponse)
async def delete_document_api(
    doc_id: uuid.UUID,
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    q = WorkspaceScopedQuery(Document).select().where(Document.id == doc_id)
    doc = (await session.execute(q)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在或不屬於此工作區")

    if doc.storage_path:
        try:
            delete_document(doc.storage_path)
        except Exception:
            pass

    await session.delete(doc)
    return ApiResponse(message="文件已刪除")
