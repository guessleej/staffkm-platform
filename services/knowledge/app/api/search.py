"""語意檢索 API — 向量 + PostgreSQL FTS Hybrid Search（RRF）"""
import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.embedder import get_embedder
from app.core.reranker import rerank
from app.core.vectorstore import hybrid_search
from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session

router = APIRouter()


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
    session: AsyncSession = Depends(get_session),
):
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
    for kb_id in body.kb_ids:
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
