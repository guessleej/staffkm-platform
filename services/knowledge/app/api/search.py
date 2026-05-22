"""語意檢索 API — 向量 + PostgreSQL FTS Hybrid Search（RRF）"""
import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.embedder import get_embedder
from app.core.reranker import rerank
from app.core.vectorstore import hybrid_search
from app.models.knowledge_base import KnowledgeBase
from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, WorkspaceScopedQuery, require_member

router = APIRouter()


async def _filter_kbs_in_workspace(
    kb_ids: list[uuid.UUID],
    ctx: TenantContext,
    session: AsyncSession,
) -> list[uuid.UUID]:
    """過濾出真正屬於當前 workspace 且通過 ACL 的 kb_id；其他靜默丟棄（避免訊息洩漏）。"""
    if not kb_ids:
        return []
    q = (
        WorkspaceScopedQuery(KnowledgeBase).select()
        .where(KnowledgeBase.id.in_(kb_ids))
    )
    rows = (await session.execute(q)).scalars().all()
    # v2.1 11-4：白名單 ACL — 對每個 KB 跑 enforce；403 視為過濾掉
    from app.core.kb_acl import enforce_kb_access
    allowed: list[uuid.UUID] = []
    for kb in rows:
        try:
            await enforce_kb_access(ctx, kb.id, session, need="read")
            allowed.append(kb.id)
        except Exception:
            continue
    return allowed


async def _expand_context(
    session: AsyncSession, hits: list[dict], window: int
) -> list[dict]:
    """P2：為每個命中段落帶回同文件相鄰段落（order_index ±window），合併進 content。

    在 rerank / top_k 之後執行 → 不影響排名，只增補最終勝出段落的上下文。
    各命中獨立開窗（相鄰命中的窗口可能重疊，視為各自獨立的引用上下文）。
    """
    if window <= 0:
        return hits
    for h in hits:
        doc_id = h.get("document_id")
        oi = h.get("order_index")
        if doc_id is None or oi is None:
            continue
        rows = await session.execute(
            text(
                "SELECT content FROM paragraphs "
                "WHERE document_id = :doc AND is_active = true "
                "AND order_index BETWEEN :lo AND :hi "
                "ORDER BY order_index"
            ),
            {"doc": str(doc_id), "lo": int(oi) - window, "hi": int(oi) + window},
        )
        parts = [r["content"] for r in rows.mappings().all() if r["content"]]
        if parts:
            h["content"] = "\n".join(parts)
    return hits


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="查詢問題")
    kb_ids: list[uuid.UUID] = Field(..., description="要搜尋的知識庫 ID 清單")
    top_k: int = Field(default=5, ge=1, le=20)
    similarity_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="向量相似度下限（僅 vector/hybrid 模式）")
    vector_weight: float = Field(default=0.7, ge=0.0, le=1.0, description="向量排名在 RRF 中的權重（1-此值 = FTS 權重）")
    search_mode: Literal["hybrid", "vector", "fts"] = Field(
        default="hybrid",
        description="hybrid=向量+FTS(RRF), vector=純向量, fts=純全文搜尋",
    )
    rrf_k: int = Field(default=60, ge=1, le=200, description="RRF 常數 k（預設 60）")
    # Reranker 設定（選填）
    reranker: dict | None = Field(default=None, description="Reranker 設定 {type, api_key, base_url, model_name}")
    rerank_top_n: int = Field(default=5, ge=1, le=20, description="Reranker 重排後取前 N 筆")
    retrieval_top_k: int = Field(default=20, ge=1, le=50, description="有 Reranker 時先取更多候選，再重排")
    # P2 上下文窗口召回：命中段落額外帶回同文件前後 N 段（0=關閉）
    context_window: int = Field(default=0, ge=0, le=5, description="每個命中段落額外帶回同文件前後 N 段的內容")


class Citation(BaseModel):
    paragraph_id: str
    content: str
    doc_name: str
    score: float
    vector_score: float = 0.0
    title: str | None = None


class SearchResponse(BaseModel):
    citations: list[Citation]
    total: int
    search_mode: str


@router.post("", response_model=ApiResponse[SearchResponse])
async def search(
    body: SearchRequest,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    # 跨 workspace 防護：只查屬於當前 workspace 的 kb_ids
    allowed_kb_ids = await _filter_kbs_in_workspace(body.kb_ids, ctx, session)
    if not allowed_kb_ids:
        return ApiResponse(data=SearchResponse(citations=[], total=0, search_mode=body.search_mode))

    # 純 FTS 模式不需要向量化
    query_embedding: list[float] = []
    if body.search_mode != "fts":
        embedder = get_embedder(
            settings.EMBEDDING_MODEL,
            settings.OPENAI_API_KEY,
            settings.EMBEDDING_BASE_URL or None,
        )
        query_embedding = await embedder.embed_text(body.query)

    fetch_k = body.retrieval_top_k if body.reranker else body.top_k

    all_results: list[dict] = []
    for kb_id in allowed_kb_ids:
        hits = await hybrid_search(
            session=session,
            kb_id=kb_id,
            query_embedding=query_embedding,
            query_text=body.query,
            top_k=fetch_k,
            similarity_threshold=body.similarity_threshold,
            vector_weight=body.vector_weight,
            search_mode=body.search_mode,
            rrf_k=body.rrf_k,
        )
        all_results.extend(hits)

    # 跨知識庫去重（依分數降序）
    seen: set[str] = set()
    deduped: list[dict] = []
    for r in sorted(all_results, key=lambda x: x["score"], reverse=True):
        pid = str(r["id"])
        if pid not in seen:
            seen.add(pid)
            deduped.append(r)

    # Reranker 重排（若設定存在）
    if body.reranker:
        deduped = await rerank(
            query=body.query,
            documents=deduped,
            reranker_config=body.reranker,
            top_n=body.rerank_top_n,
        )
        final_results = deduped
    else:
        final_results = deduped[: body.top_k]

    # P2 上下文窗口：對最終命中段落帶回同文件相鄰段落（rerank 後執行，不影響排名）
    if body.context_window > 0:
        final_results = await _expand_context(session, final_results, body.context_window)

    citations = [
        Citation(
            paragraph_id=str(r["id"]),
            content=r["content"],
            doc_name=r["doc_name"],
            score=round(float(r["score"]), 6),
            vector_score=round(float(r.get("vector_score", 0.0)), 6),
            title=r.get("title"),
        )
        for r in final_results
    ]
    return ApiResponse(
        data=SearchResponse(
            citations=citations,
            total=len(citations),
            search_mode=body.search_mode,
        )
    )
