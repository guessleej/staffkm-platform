"""知識庫 CRUD API（RFC-001 Stage 2 — workspace-scoped）"""
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import KnowledgeBase, KBStatus
from staffkm_core.audit import record_audit
from staffkm_core.schemas.response import ApiResponse, PageMeta, PagedResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import (
    TenantContext, WorkspaceScopedQuery,
    require_member, require_writer, require_admin,
)

logger = logging.getLogger(__name__)
router = APIRouter()


async def _safe_audit(session: AsyncSession, **kwargs) -> None:
    try:
        await record_audit(session, **kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.warning("audit record failed: %s", exc)


class KBCreate(BaseModel):
    name: str
    description: str | None = None
    embedding_model: str = "snowflake-arctic-embed2"
    is_public: bool = False
    # RFC-006 切片技術升級
    chunk_strategy: str = "auto"      # auto / recursive / markdown / qa
    chunk_size:     int = 512
    chunk_overlap:  int = 64


class KBUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_public: bool | None = None
    chunk_strategy: str | None = None
    chunk_size:     int | None = None
    chunk_overlap:  int | None = None


class KBOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    status: str
    embedding_model: str
    is_public: bool
    document_count: int = 0
    chunk_strategy: str = "auto"
    chunk_size:     int = 512
    chunk_overlap:  int = 64
    graph_enabled:  bool = False   # v5.11.x GraphRAG：卡片顯示是否啟用知識圖譜
    # Sprint 18-C：來源資訊（給卡片 badge 用）
    source_type: str = "manual"
    source_url:  str | None = None
    sync_status: str | None = None
    last_synced_at: datetime | None = None

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
    request: Request,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    kb = KnowledgeBase(workspace_id=ctx.workspace_id, **body.model_dump())
    session.add(kb)
    await session.flush()
    await _safe_audit(
        session,
        workspace_id=ctx.workspace_id,
        actor_user_id=ctx.user_id,
        actor_username=None,
        action="create",
        entity_type="kb",
        entity_id=str(kb.id),
        entity_label=kb.name,
        detail={"embedding_model": body.embedding_model, "is_public": body.is_public},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
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
    request: Request,
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    q = WorkspaceScopedQuery(KnowledgeBase).select().where(KnowledgeBase.id == kb_id)
    kb = (await session.execute(q)).scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="知識庫不存在或不屬於此工作區")
    kb_name = kb.name
    await session.delete(kb)
    await _safe_audit(
        session,
        workspace_id=ctx.workspace_id,
        actor_user_id=ctx.user_id,
        actor_username=None,
        action="delete",
        entity_type="kb",
        entity_id=str(kb_id),
        entity_label=kb_name,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    return ApiResponse(message="知識庫已刪除")


# ═══════════════════════════════════════════════════════════════════════
#  Round 10-5 / RFC-013：Workflow KB
# ═══════════════════════════════════════════════════════════════════════
class ConvertToWorkflowReq(BaseModel):
    source_workflow_id: uuid.UUID


@router.post("/{kb_id}/convert-to-workflow", response_model=ApiResponse)
async def convert_to_workflow_kb(
    kb_id: uuid.UUID,
    body: ConvertToWorkflowReq,
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """把現有手動 KB 轉換為 workflow KB（不可撤回）。

    後續寫入只能透過指定 workflow 的 kb_writer node；
    inline-write endpoint + workflow node 留給 v2.1 中段（RFC-013）。
    """
    from sqlalchemy import text
    q = WorkspaceScopedQuery(KnowledgeBase).select().where(KnowledgeBase.id == kb_id)
    kb = (await session.execute(q)).scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="知識庫不存在或不屬於此工作區")

    # 取目前 source_type；model 尚未加欄位，用 raw SQL
    r = await session.execute(
        text("SELECT source_type FROM knowledge_bases WHERE id = :id"),
        {"id": str(kb_id)},
    )
    row = r.fetchone()
    if row and (row._mapping.get("source_type") == "workflow"):
        raise HTTPException(status_code=400, detail="此 KB 已是 workflow KB；無法重複轉換")

    await session.execute(
        text(
            "UPDATE knowledge_bases SET source_type = 'workflow', "
            "  source_workflow_id = :wf, updated_at = now() "
            "WHERE id = :id AND workspace_id = :ws"
        ),
        {"wf": str(body.source_workflow_id), "id": str(kb_id), "ws": str(ctx.workspace_id)},
    )
    await session.commit()
    return ApiResponse(message="已轉換為 workflow KB（不可撤回）", data={
        "kb_id": str(kb_id),
        "source_type": "workflow",
        "source_workflow_id": str(body.source_workflow_id),
    })


# ═══════════════════════════════════════════════════════════════════════
#  v2.8 H1：KB 全 metadata 匯出 / 匯入
# ═══════════════════════════════════════════════════════════════════════
from io import BytesIO
from fastapi import File, UploadFile
from fastapi.responses import StreamingResponse


@router.get("/{kb_id}/export")
async def export_kb_full(
    kb_id: uuid.UUID,
    include_embeddings: int = 0,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    """整 KB 匯出成 ZIP（含 documents / paragraphs metadata）。

    `?include_embeddings=1` 時連 paragraph 向量一起匯出（base64 packed float32）。
    """
    from sqlalchemy import text
    from app.core.exporter import kb_full_export_zip
    from app.models.knowledge_base import Document, Paragraph

    # 1. KB 本體
    q = WorkspaceScopedQuery(KnowledgeBase).select().where(KnowledgeBase.id == kb_id)
    kb = (await session.execute(q)).scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="知識庫不存在或不屬於此工作區")

    kb_meta = {
        "schema_version":      1,
        "name":                kb.name,
        "description":         kb.description,
        "embedding_model":     kb.embedding_model,
        "vector_store_type":   kb.vector_store_type,
        "chunk_strategy":      kb.chunk_strategy,
        "chunk_size":          kb.chunk_size,
        "chunk_overlap":       kb.chunk_overlap,
        "is_public":           kb.is_public,
        "source_type":         kb.source_type,
        "settings":            kb.meta or {},
    }

    # 2. Documents
    doc_rows = (await session.execute(
        WorkspaceScopedQuery(Document).select().where(Document.knowledge_base_id == kb_id)
    )).scalars().all()
    docs: list[dict] = []
    para_by_doc: dict[str, list[dict]] = {}
    doc_ids = [d.id for d in doc_rows]

    for d in doc_rows:
        docs.append({
            "id":              str(d.id),
            "name":            d.name,
            "file_type":       d.file_type,
            "file_size":       d.file_size,
            "status":          d.status,
            "tags":            d.tags or [],
            "hit_strategy":    d.hit_strategy or "rag",
            "is_enabled":      bool(d.is_enabled),
            "meta":            d.meta or {},
            "questions":       d.questions or [],
            "paragraph_count": d.paragraph_count,
            "char_count":      d.char_count,
            "created_at":      d.created_at.isoformat() if d.created_at else None,
        })

    # 3. Paragraphs（一次 query）
    if doc_ids:
        from sqlalchemy import select as sql_select
        para_rows = (await session.execute(
            sql_select(Paragraph)
            .where(Paragraph.document_id.in_(doc_ids))
            .where(Paragraph.workspace_id == ctx.workspace_id)
            .order_by(Paragraph.document_id, Paragraph.order_index)
        )).scalars().all()
        for p in para_rows:
            para_by_doc.setdefault(str(p.document_id), []).append({
                "id":          str(p.id),
                "title":       p.title,
                "content":     p.content,
                "order_index": p.order_index,
                "char_count":  p.char_count,
                "is_active":   bool(p.is_active),
                "meta":        p.meta or {},
                "qa_pairs":    p.qa_pairs or [],
            })

    # 4. Embeddings（可選）
    embeddings: dict[str, list[float]] | None = None
    if include_embeddings:
        # paragraph_embeddings 不在 ORM 中，走 raw SQL；CAST 規則參考 CLAUDE.md §8
        rows = await session.execute(text(
            "SELECT pe.paragraph_id, pe.embedding "
            "FROM paragraph_embeddings pe "
            "JOIN paragraphs p ON p.id = pe.paragraph_id "
            "WHERE p.knowledge_base_id = CAST(:kb AS uuid)"
        ), {"kb": str(kb_id)})
        embeddings = {}
        for r in rows.fetchall():
            pid = str(r._mapping["paragraph_id"])
            emb = r._mapping["embedding"]
            # pgvector 在 asyncpg 下通常以 string "[0.1,0.2,...]" 或 list 來
            if isinstance(emb, str):
                emb = [float(x) for x in emb.strip("[]").split(",") if x]
            elif emb is not None:
                emb = list(map(float, emb))
            if emb:
                embeddings[pid] = emb

    data = kb_full_export_zip(kb_meta, docs, para_by_doc, embeddings_by_paragraph=embeddings)
    return StreamingResponse(
        BytesIO(data),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="kb-{kb_id}.full.zip"'},
    )


@router.post("/import", response_model=ApiResponse)
async def import_kb_full(
    file: UploadFile = File(...),
    rename_to: str | None = None,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    """匯入 KB（多 part zip）。
    一律建新 KB（避免覆蓋舊資料）；upload 後 paragraph 留待 worker 重新 embed。
    若 ZIP 帶 embeddings/{pid}.b64 仍會被忽略（v2.8 簡化版）；
    後續 v2.9 可加 `?include_embeddings=1` 還原以省 embed cost。
    """
    import json as _json
    import zipfile as _zip
    from app.models.knowledge_base import Document, DocStatus, Paragraph

    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="僅接受 .zip 檔")

    raw = await file.read()
    try:
        zf = _zip.ZipFile(BytesIO(raw), "r")
    except _zip.BadZipFile:
        raise HTTPException(status_code=400, detail="ZIP 檔損毀")

    names = set(zf.namelist())
    if "kb.json" not in names:
        raise HTTPException(status_code=400, detail="ZIP 缺少 kb.json")
    try:
        kb_meta = _json.loads(zf.read("kb.json"))
        docs_meta: list[dict] = _json.loads(zf.read("documents.json")) if "documents.json" in names else []
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"kb.json / documents.json 解析失敗：{e}")

    # 1. 建新 KB
    new_kb = KnowledgeBase(
        workspace_id=ctx.workspace_id,
        name=(rename_to or kb_meta.get("name") or "Imported KB")[:128],
        description=kb_meta.get("description"),
        embedding_model=kb_meta.get("embedding_model") or "snowflake-arctic-embed2",
        vector_store_type=kb_meta.get("vector_store_type") or "pgvector",
        chunk_strategy=kb_meta.get("chunk_strategy") or "auto",
        chunk_size=kb_meta.get("chunk_size") or 512,
        chunk_overlap=kb_meta.get("chunk_overlap") or 64,
        is_public=bool(kb_meta.get("is_public", False)),
        meta=kb_meta.get("settings") or {},
    )
    session.add(new_kb)
    await session.flush()

    doc_count = 0
    para_count = 0
    docs_to_embed: list[tuple[str, str]] = []  # (doc_id, name) — 匯入後背景補 embed
    for dm in docs_meta:
        new_doc = Document(
            workspace_id=ctx.workspace_id,
            knowledge_base_id=new_kb.id,
            name=dm.get("name") or "untitled",
            file_type=dm.get("file_type") or "txt",
            file_size=int(dm.get("file_size") or 0),
            status=DocStatus.READY,
            tags=dm.get("tags") or [],
            hit_strategy=dm.get("hit_strategy") or "rag",
            is_enabled=bool(dm.get("is_enabled", True)),
            meta=dm.get("meta") or {},
            questions=dm.get("questions") or [],
            paragraph_count=int(dm.get("paragraph_count") or 0),
            char_count=int(dm.get("char_count") or 0),
        )
        session.add(new_doc)
        await session.flush()
        doc_count += 1

        # 對應 paragraphs/{old_doc_id}.json
        old_doc_id = str(dm.get("id"))
        para_path = f"paragraphs/{old_doc_id}.json"
        if para_path in names:
            try:
                paras: list[dict] = _json.loads(zf.read(para_path))
            except Exception:
                paras = []
            doc_para_count = 0
            for p in paras:
                session.add(Paragraph(
                    workspace_id=ctx.workspace_id,
                    document_id=new_doc.id,
                    knowledge_base_id=new_kb.id,
                    content=p.get("content") or "",
                    title=p.get("title"),
                    order_index=int(p.get("order_index") or 0),
                    char_count=int(p.get("char_count") or len(p.get("content") or "")),
                    is_active=bool(p.get("is_active", True)),
                    meta=p.get("meta") or {},
                    qa_pairs=p.get("qa_pairs") or [],
                ))
                para_count += 1
                doc_para_count += 1
            if doc_para_count:
                docs_to_embed.append((str(new_doc.id), new_doc.name))

    await session.commit()

    # v5.10.x P0-1：匯入的段落沒有向量 → 對每個 doc 背景補 embed（inline 模式）
    from app.tasks.process_document import process_document
    enqueued = 0
    for doc_id, doc_name in docs_to_embed:
        process_document.apply_async(args=[doc_id, "", doc_name], kwargs={"inline": True})
        enqueued += 1
    logger.info("kb_import_reembed_enqueued kb=%s docs=%d paras=%d", new_kb.id, enqueued, para_count)

    return ApiResponse(
        message=f"KB 匯入成功；已自動排程 {enqueued} 份文件的段落向量化（背景處理中）。",
        data={
            "kb_id":           str(new_kb.id),
            "documents":       doc_count,
            "paragraphs":      para_count,
            "reembed_docs":    enqueued,
            "embeddings_note": "段落向量由後台 inline re-embed 自動補齊。",
        },
    )


@router.get("/{kb_id}/source-info", response_model=ApiResponse)
async def get_source_info(
    kb_id: uuid.UUID,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    """回傳 KB source 資訊（manual / workflow）；workflow 時帶 source_workflow_id。"""
    from sqlalchemy import text
    r = await session.execute(
        text(
            "SELECT id, name, source_type, source_workflow_id "
            "FROM knowledge_bases WHERE id = :id AND workspace_id = :ws"
        ),
        {"id": str(kb_id), "ws": str(ctx.workspace_id)},
    )
    row = r.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="知識庫不存在或不屬於此工作區")
    return ApiResponse(data=dict(row._mapping))


# ── RFC-014 GraphRAG（MVP v5.11.0）─────────────────────────────────────
@router.post("/{kb_id}/graph/rebuild", response_model=ApiResponse)
async def rebuild_kb_graph(
    kb_id: uuid.UUID,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    """開啟此 KB 的 graph_enabled 並背景重建知識圖譜（對既有文件）。"""
    kb = (await session.execute(
        WorkspaceScopedQuery(KnowledgeBase).select().where(KnowledgeBase.id == kb_id)
    )).scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="知識庫不存在或不屬於此工作區")
    kb.graph_enabled = True
    await session.commit()
    from app.tasks.build_graph import build_graph
    task = build_graph.delay(str(kb_id), str(ctx.workspace_id), None)
    return ApiResponse(
        message="已開啟 GraphRAG 並排程重建圖譜（背景處理中）",
        data={"kb_id": str(kb_id), "graph_enabled": True, "task_id": task.id},
    )


@router.post("/{kb_id}/graph/disable", response_model=ApiResponse)
async def disable_kb_graph(
    kb_id: uuid.UUID,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    """關閉此 KB 的 GraphRAG（查詢即不再走 graph 召回；既有圖資料保留）。"""
    kb = (await session.execute(
        WorkspaceScopedQuery(KnowledgeBase).select().where(KnowledgeBase.id == kb_id)
    )).scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="知識庫不存在或不屬於此工作區")
    kb.graph_enabled = False
    await session.commit()
    return ApiResponse(message="已關閉 GraphRAG", data={"kb_id": str(kb_id), "graph_enabled": False})


@router.get("/{kb_id}/graph/communities", response_model=ApiResponse)
async def list_kb_communities(
    kb_id: uuid.UUID,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    """Phase 3：列出此 KB 的實體社群（連通分量 + LLM 摘要），含成員實體名。"""
    kb = (await session.execute(
        WorkspaceScopedQuery(KnowledgeBase).select().where(KnowledgeBase.id == kb_id)
    )).scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="知識庫不存在或不屬於此工作區")
    from sqlalchemy import text
    rows = await session.execute(
        text("""
            SELECT c.id, c.title, c.summary, c.entity_ids, c.cohesion_score,
                   (SELECT json_agg(e.name) FROM kb_entities e
                    WHERE e.id IN (SELECT jsonb_array_elements_text(c.entity_ids)::uuid)) AS entity_names
            FROM kb_communities c
            WHERE c.knowledge_base_id = CAST(:kb AS uuid)
            ORDER BY c.cohesion_score DESC NULLS LAST, jsonb_array_length(c.entity_ids) DESC
        """),
        {"kb": str(kb_id)},
    )
    communities = [
        {
            "id": str(r["id"]), "title": r["title"], "summary": r["summary"],
            "size": len(r["entity_ids"] or []), "cohesion_score": r["cohesion_score"],
            "entities": r["entity_names"] or [],
        }
        for r in rows.mappings().all()
    ]
    # graph 總覽計數（給可視化卡片）
    counts = (await session.execute(
        text("""
            SELECT
              (SELECT count(*) FROM kb_entities  WHERE knowledge_base_id = CAST(:kb AS uuid)) AS entities,
              (SELECT count(*) FROM kb_relations WHERE knowledge_base_id = CAST(:kb AS uuid)) AS relations
        """),
        {"kb": str(kb_id)},
    )).mappings().first()
    return ApiResponse(data={
        "kb_id": str(kb_id),
        "graph_enabled": bool(kb.graph_enabled),
        "entities": int(counts["entities"]) if counts else 0,
        "relations": int(counts["relations"]) if counts else 0,
        "communities": communities,
        "total": len(communities),
    })
