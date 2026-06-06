"""文件上傳與管理 API（RFC-001 Stage 2 — workspace-scoped）"""
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import text
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
    *, need: str = "read",
) -> KnowledgeBase:
    """確認 kb 屬於當前 workspace + 通過 ACL；否則 404 / 403。"""
    q = WorkspaceScopedQuery(KnowledgeBase).select().where(KnowledgeBase.id == kb_id)
    kb = (await session.execute(q)).scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="知識庫不存在或不屬於此工作區")
    # v2.1 11-4：白名單 enforce
    from app.core.kb_acl import enforce_kb_access
    await enforce_kb_access(ctx, kb_id, session, need=need)  # type: ignore[arg-type]
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

    # v5.13: 音檔走地端 ASR（在 knowledge-worker 跑）。可用性以 worker 為準：記憶體不足時
    #   worker 的 transcribe() 會 raise → process_document 把文件標 error 並存明確訊息，
    #   不在此（API 容器）預檢記憶體（查的是錯的容器，worker 記憶體才是關鍵）。
    contents = await file.read()
    # v5.13: 音檔通常遠大於文件 → 套較寬的上限
    is_audio = ext in settings.AUDIO_EXTENSIONS
    max_mb = settings.MAX_AUDIO_FILE_SIZE_MB if is_audio else settings.MAX_FILE_SIZE_MB
    if len(contents) > max_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"檔案超過 {max_mb}MB 限制")

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
    page: int = 1,
    page_size: int = 1000,
):
    await _verify_kb_in_workspace(kb_id, ctx, session)
    # v5.12: 加分頁 + hard cap 防 OOM — 單一 KB 文件數上千時原本一次全載
    page = max(1, page)
    page_size = min(max(1, page_size), 2000)
    q = (
        WorkspaceScopedQuery(Document).select()
        .where(Document.knowledge_base_id == kb_id)
        .order_by(Document.created_at.desc())
        .limit(page_size).offset((page - 1) * page_size)
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
            # Round 10-1: MaxKB parity
            "tags":         d.tags or [],
            "hit_strategy": d.hit_strategy or "rag",
            "is_enabled":   bool(d.is_enabled),
            "created_at":   d.created_at.isoformat() if d.created_at else None,
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

    # v5.13: milvus 模式先撈段落 id（CASCADE 刪 PG 後查不到），刪 PG 後再清 Milvus 向量
    from app.core import milvus_store
    para_ids: list = []
    if milvus_store.is_enabled():
        rows = await session.execute(
            text("SELECT id FROM paragraphs WHERE document_id = :d"), {"d": str(doc_id)}
        )
        para_ids = [str(r[0]) for r in rows.fetchall()]

    await session.delete(doc)
    await session.commit()
    await milvus_store.safe_delete_by_paragraphs(para_ids)
    return ApiResponse(message="文件已刪除")


# ═══════════════════════════════════════════════════════════════════════
#  Round 10-1：文檔操作擴充（MaxKB parity）
# ═══════════════════════════════════════════════════════════════════════
from io import BytesIO
from typing import Any
from fastapi import Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field


class DocSettingsPatch(BaseModel):
    """單一或部分欄位更新；空欄不動。"""
    tags:         list[str] | None = None
    hit_strategy: str | None = Field(default=None, pattern="^(rag|direct|both)$")
    is_enabled:   bool | None = None
    name:         str | None = None


class DocMigrate(BaseModel):
    target_kb_id: uuid.UUID


class DocBatchOp(BaseModel):
    document_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=500)


async def _load_doc(doc_id, session, ctx: TenantContext | None = None, *, need: str = "read") -> Document:
    q = WorkspaceScopedQuery(Document).select().where(Document.id == doc_id)
    doc = (await session.execute(q)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在或不屬於此工作區")
    if ctx is not None:
        from app.core.kb_acl import enforce_kb_access
        await enforce_kb_access(ctx, doc.knowledge_base_id, session, need=need)  # type: ignore[arg-type]
    return doc


@router.patch("/doc/{doc_id}/settings", response_model=ApiResponse)
async def update_doc_settings(
    doc_id: uuid.UUID,
    body: DocSettingsPatch,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    """更新文件設定：tags / hit_strategy / is_enabled / name。"""
    doc = await _load_doc(doc_id, session, ctx, need="edit")
    data = body.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(doc, k, v)
    await session.commit()
    return ApiResponse(message="文件設定已更新", data={
        "tags": doc.tags or [], "hit_strategy": doc.hit_strategy,
        "is_enabled": doc.is_enabled, "name": doc.name,
    })


@router.post("/doc/{doc_id}/migrate", response_model=ApiResponse)
async def migrate_document(
    doc_id: uuid.UUID,
    body: DocMigrate,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    """把文件搬到同 workspace 的另一個 KB。

    paragraphs / embeddings 一起跟著走（外鍵 ON DELETE CASCADE 不適用，這裡只改 knowledge_base_id）。
    """
    doc = await _load_doc(doc_id, session, ctx, need="edit")
    # 遷移到的目標 KB 至少要 edit 權限
    target = await _verify_kb_in_workspace(body.target_kb_id, ctx, session, need="edit")
    if doc.knowledge_base_id == target.id:
        return ApiResponse(message="目標 KB 與目前相同；無變動")
    doc.knowledge_base_id = target.id
    await session.commit()
    return ApiResponse(message="文件已遷移", data={
        "document_id": str(doc.id),
        "target_kb_id": str(target.id),
    })


@router.get("/doc/{doc_id}/download")
async def download_original(
    doc_id: uuid.UUID,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    """下載原始檔。"""
    from app.core.storage import download_document
    doc = await _load_doc(doc_id, session, ctx, need="read")
    if not doc.storage_path:
        raise HTTPException(status_code=404, detail="文件原檔不存在")
    try:
        data = download_document(doc.storage_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"讀取原檔失敗：{e}") from e
    return StreamingResponse(
        BytesIO(data),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{doc.name}"',
        },
    )


@router.post("/doc/{doc_id}/replace", response_model=ApiResponse)
async def replace_original(
    doc_id: uuid.UUID,
    file: UploadFile = File(...),
    keep_chunks: bool = Form(False),
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    """以新檔取代原檔。預設會清掉舊 paragraphs 並重新處理；keep_chunks=true 則只換原檔不重切。"""
    doc = await _load_doc(doc_id, session, ctx, need="edit")
    ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支援的檔案格式：{ext}")
    contents = await file.read()
    if len(contents) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"檔案超過 {settings.MAX_FILE_SIZE_MB}MB 限制")

    # 刪舊原檔
    if doc.storage_path:
        try:
            delete_document(doc.storage_path)
        except Exception:
            pass

    new_key = f"documents/{doc.id}/{file.filename}"
    new_path = upload_document(contents, new_key)
    doc.storage_path = new_path
    doc.file_size    = len(contents)
    doc.file_type    = ext.lstrip(".")
    doc.name         = file.filename
    doc.error_message = None

    task_id: str | None = None
    if not keep_chunks:
        # 觸發重切：清 paragraphs 由 process_document 自己處理（PENDING 標記即可）
        doc.status = DocStatus.PENDING
        doc.paragraph_count = 0
        doc.char_count = 0
        task = process_document.delay(str(doc.id))
        task_id = task.id
        doc.meta = {**(doc.meta or {}), "celery_task_id": task_id, "progress": 0}

    await session.commit()
    return ApiResponse(message="文件已替換", data={
        "document_id": str(doc.id),
        "task_id":     task_id,
        "keep_chunks": keep_chunks,
    })


@router.post("/{kb_id}/batch-toggle", response_model=ApiResponse)
async def batch_toggle(
    kb_id: uuid.UUID,
    body: DocBatchOp,
    enabled: bool = True,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    """批量啟用 / 停用文件。"""
    await _verify_kb_in_workspace(kb_id, ctx, session)
    from sqlalchemy import update as sql_update
    res = await session.execute(
        sql_update(Document)
        .where(Document.id.in_(body.document_ids))
        .where(Document.workspace_id == ctx.workspace_id)
        .where(Document.knowledge_base_id == kb_id)
        .values(is_enabled=enabled)
    )
    await session.commit()
    return ApiResponse(message=f"{'啟用' if enabled else '停用'} 已套用",
                       data={"updated": res.rowcount})


@router.post("/{kb_id}/batch-delete", response_model=ApiResponse)
async def batch_delete(
    kb_id: uuid.UUID,
    body: DocBatchOp,
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """批量刪除文件（含原檔）。"""
    await _verify_kb_in_workspace(kb_id, ctx, session)
    q = (
        WorkspaceScopedQuery(Document).select()
        .where(Document.id.in_(body.document_ids))
        .where(Document.knowledge_base_id == kb_id)
    )
    docs: list[Document] = list((await session.execute(q)).scalars().all())
    for d in docs:
        if d.storage_path:
            try: delete_document(d.storage_path)
            except Exception: pass
        await session.delete(d)
    await session.commit()
    return ApiResponse(message="批量刪除完成", data={"deleted": len(docs)})


# ── 標籤管理（workspace 級）──────────────────────────────────────────
@router.get("/tags", response_model=ApiResponse)
async def list_workspace_tags(
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    """彙整 workspace 內所有文件出現過的標籤 + 出現次數。"""
    from sqlalchemy import text
    rows = await session.execute(
        text(
            "SELECT tag, COUNT(*) AS n "
            "FROM documents d, jsonb_array_elements_text(d.tags) AS tag "
            "WHERE d.workspace_id = :ws "
            "GROUP BY tag ORDER BY n DESC, tag"
        ),
        {"ws": str(ctx.workspace_id)},
    )
    items: list[dict[str, Any]] = [
        {"tag": r._mapping["tag"], "count": int(r._mapping["n"])}
        for r in rows.fetchall()
    ]
    return ApiResponse(data=items)


# ═══════════════════════════════════════════════════════════════════════
#  Round 10-2：文檔層級 Q&A 批量生成
# ═══════════════════════════════════════════════════════════════════════
class DocGenerateQAReq(BaseModel):
    per_paragraph: int = Field(default=2, ge=1, le=5)
    max_paragraphs: int = Field(default=20, ge=1, le=200)
    model: str | None = None
    overwrite: bool = False


@router.post("/doc/{doc_id}/generate-questions", response_model=ApiResponse)
async def generate_document_questions(
    doc_id: uuid.UUID,
    body: DocGenerateQAReq,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    """對文件內每個段落跑 LLM 產 Q&A，彙整出 document.questions（給 application suggested_questions 用）。

    為防暴衝：預設最多處理前 20 段、每段最多 2 組。
    overwrite=False 時段落已有 qa_pairs 會跳過。
    """
    from app.core.qa_generator import generate_qa_for_text
    from app.models.knowledge_base import Paragraph
    from sqlalchemy import select as sql_select

    doc = await _load_doc(doc_id, session, ctx, need="edit")
    rows = await session.execute(
        sql_select(Paragraph)
        .where(Paragraph.document_id == doc.id)
        .where(Paragraph.workspace_id == ctx.workspace_id)
        .order_by(Paragraph.order_index)
        .limit(body.max_paragraphs)
    )
    paragraphs: list[Paragraph] = list(rows.scalars().all())
    if not paragraphs:
        return ApiResponse(message="文件尚無段落；請先等待向量化完成")

    processed = 0
    aggregated_qs: list[str] = []
    last_error: str | None = None
    for p in paragraphs:
        if not body.overwrite and p.qa_pairs:
            for pair in p.qa_pairs:
                if pair.get("question"):
                    aggregated_qs.append(pair["question"])
            continue
        try:
            new_pairs = await generate_qa_for_text(p.content, n=body.per_paragraph, model=body.model)
        except RuntimeError as e:
            last_error = str(e)
            break
        p.qa_pairs = new_pairs
        for pair in new_pairs:
            aggregated_qs.append(pair["question"])
        processed += 1

    # 去重 + 保留前 20 個給 doc.questions
    seen: set[str] = set()
    uniq_qs: list[str] = []
    for q in aggregated_qs:
        if q in seen:
            continue
        seen.add(q)
        uniq_qs.append(q)
        if len(uniq_qs) >= 20:
            break
    doc.questions = uniq_qs
    await session.commit()

    return ApiResponse(
        message=(f"已處理 {processed} 段，彙整 {len(uniq_qs)} 個常見問題"
                 + (f"；於最後一段失敗：{last_error}" if last_error else "")),
        data={"processed": processed, "questions": uniq_qs},
    )


@router.get("/doc/{doc_id}/questions", response_model=ApiResponse)
async def list_document_questions(
    doc_id: uuid.UUID,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    doc = await _load_doc(doc_id, session, ctx, need="read")
    return ApiResponse(data=doc.questions or [])


# ═══════════════════════════════════════════════════════════════════════
#  Round 10-3：匯出（Excel / ZIP）
# ═══════════════════════════════════════════════════════════════════════
class ExportSelectReq(BaseModel):
    """指定 document_ids；空陣列 = 整個 KB 全匯。"""
    document_ids: list[uuid.UUID] = Field(default_factory=list)


def _doc_to_dict(d: Document) -> dict[str, Any]:
    return {
        "id":              d.id,
        "name":            d.name,
        "file_type":       d.file_type,
        "file_size":       d.file_size,
        "status":          d.status,
        "paragraph_count": d.paragraph_count,
        "char_count":      d.char_count,
        "tags":            d.tags or [],
        "hit_strategy":    d.hit_strategy,
        "is_enabled":      d.is_enabled,
        "created_at":      d.created_at.isoformat() if d.created_at else None,
        "questions":       d.questions or [],
    }


async def _resolve_docs(
    session, ctx: TenantContext, kb_id: uuid.UUID, doc_ids: list[uuid.UUID],
) -> list[Document]:
    await _verify_kb_in_workspace(kb_id, ctx, session)
    q = (
        WorkspaceScopedQuery(Document).select()
        .where(Document.knowledge_base_id == kb_id)
    )
    if doc_ids:
        q = q.where(Document.id.in_(doc_ids))
    return list((await session.execute(q)).scalars().all())


@router.post("/{kb_id}/export/excel")
async def export_documents_excel(
    kb_id: uuid.UUID,
    body: ExportSelectReq,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    from app.core.exporter import to_excel_bytes
    docs = await _resolve_docs(session, ctx, kb_id, body.document_ids)
    data = to_excel_bytes([_doc_to_dict(d) for d in docs])
    return StreamingResponse(
        BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="kb-{kb_id}.xlsx"'},
    )


@router.post("/{kb_id}/export/zip")
async def export_documents_zip(
    kb_id: uuid.UUID,
    body: ExportSelectReq,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    from app.core.exporter import to_zip_bytes
    from app.models.knowledge_base import Paragraph
    from sqlalchemy import select as sql_select

    docs = await _resolve_docs(session, ctx, kb_id, body.document_ids)
    doc_dicts = [_doc_to_dict(d) for d in docs]

    # 預載所有 paragraphs（一次 query，避免 N+1）
    doc_ids = [d.id for d in docs]
    paras_by_doc: dict[str, list[dict]] = {str(i): [] for i in doc_ids}
    if doc_ids:
        rows = await session.execute(
            sql_select(Paragraph)
            .where(Paragraph.document_id.in_(doc_ids))
            .where(Paragraph.workspace_id == ctx.workspace_id)
            .order_by(Paragraph.document_id, Paragraph.order_index)
        )
        for p in rows.scalars().all():
            paras_by_doc.setdefault(str(p.document_id), []).append({
                "order_index": p.order_index,
                "title":       p.title,
                "content":     p.content,
            })

    def _get_paragraphs(doc_id: str) -> list[dict]:
        return paras_by_doc.get(doc_id, [])

    # 彙整所有 doc.questions 為 ZIP 根 questions.json
    all_qs: list[str] = []
    seen: set[str] = set()
    for d in doc_dicts:
        for q in d.get("questions") or []:
            if q not in seen:
                seen.add(q)
                all_qs.append(q)

    data = to_zip_bytes(doc_dicts, _get_paragraphs, questions_aggregate=all_qs)
    return StreamingResponse(
        BytesIO(data),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="kb-{kb_id}.zip"'},
    )
