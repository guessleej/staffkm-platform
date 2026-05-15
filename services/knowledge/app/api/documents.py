"""文件上傳與管理 API"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.storage import upload_document, delete_document
from app.models.knowledge_base import Document, DocStatus
from app.tasks.process_document import process_document
from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session

router = APIRouter()


@router.post("/{kb_id}/upload", response_model=ApiResponse)
async def upload_document_api(
    kb_id: uuid.UUID,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支援的檔案格式：{ext}")

    contents = await file.read()
    if len(contents) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"檔案超過 {settings.MAX_FILE_SIZE_MB}MB 限制")

    doc = Document(
        knowledge_base_id=kb_id,
        name=file.filename,
        file_type=ext.lstrip("."),
        file_size=len(contents),
        status=DocStatus.PENDING,
    )
    session.add(doc)
    await session.flush()  # 取得 doc.id，尚未 commit

    # 決定 MinIO 路徑並上傳
    minio_key = f"documents/{doc.id}/{file.filename}"
    try:
        upload_document(contents, minio_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"檔案儲存失敗：{e}")

    doc.storage_path = minio_key
    doc.meta = {"progress": 0, "progress_message": "等待處理…"}
    # commit — 讓 Celery worker 能讀到這筆 document
    await session.commit()

    # 派發 Celery 任務（countdown=1 確保 commit 已完成）
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
async def list_documents(kb_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    from sqlalchemy import select
    result = await session.execute(
        select(Document).where(Document.knowledge_base_id == kb_id)
    )
    docs = result.scalars().all()
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
async def delete_document_api(doc_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    doc = await session.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 從 MinIO 刪除（失敗不中斷，僅記錄）
    if doc.storage_path:
        try:
            delete_document(doc.storage_path)
        except Exception:
            pass

    await session.delete(doc)
    return ApiResponse(message="文件已刪除")
