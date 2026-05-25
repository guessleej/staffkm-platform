"""命中測試 API — 測試查詢在知識庫的檢索效果"""
import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.runtime_models import get_active_embedder
from app.config import settings
from app.core.vectorstore import hybrid_search
from app.models.knowledge_base import KnowledgeBase
from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, WorkspaceScopedQuery, require_member
from fastapi import HTTPException

router = APIRouter()


class HitTestRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    kb_id: uuid.UUID
    top_k: int = Field(default=10, ge=1, le=20)
    similarity_threshold: float = Field(default=0.3)
    vector_weight: float = Field(default=0.7)
    search_mode: Literal["hybrid", "vector", "fts"] = Field(default="hybrid")
    rrf_k: int = Field(default=60, ge=1, le=200)
    reranker: dict | None = Field(
        default=None,
        description="reranker 設定（type/api_key/model_name/base_url ...）；None 不啟用",
    )
    rerank_top_n: int = Field(default=5, ge=1, le=20)


@router.post("", response_model=ApiResponse)
async def hit_test(
    body: HitTestRequest,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    # 驗證 kb_id 屬於當前 workspace
    kb_q = WorkspaceScopedQuery(KnowledgeBase).select().where(KnowledgeBase.id == body.kb_id)
    if not (await session.execute(kb_q)).scalar_one_or_none():
        raise HTTPException(status_code=404, detail="知識庫不存在或不屬於此工作區")

    query_embedding: list[float] = []
    if body.search_mode != "fts":
        embedder = await get_active_embedder(session)
        query_embedding = await embedder.embed_text(body.query)

    hits = await hybrid_search(
        session=session,
        kb_id=body.kb_id,
        query_embedding=query_embedding,
        query_text=body.query,
        top_k=body.top_k,
        similarity_threshold=body.similarity_threshold,
        vector_weight=body.vector_weight,
        search_mode=body.search_mode,
        rrf_k=body.rrf_k,
    )

    # C3 — 可選 reranker
    reranked_ids: dict[str, float] = {}
    if body.reranker:
        from app.core.reranker import rerank

        reranked = await rerank(
            query=body.query,
            documents=hits,
            reranker_config=body.reranker,
            top_n=body.rerank_top_n,
        )
        # 只用 reranker 真實塞的 relevance_score；缺失 = reranker 失敗/不支援
        # v5.0.12 移除 (n-idx)/n fake fallback (user 誤以為 rerank 成功)
        for doc in reranked:
            pid = str(doc["id"])
            rs = doc.get("relevance_score")
            if rs is not None:
                reranked_ids[pid] = float(rs)
        # 把 reranked 順序套回 hits（保留沒入選的在後面）
        order_map = {str(d["id"]): i for i, d in enumerate(reranked)}
        hits = sorted(hits, key=lambda h: order_map.get(str(h["id"]), 10_000))
        # 若 reranker 完全沒回 relevance_score → 視為失敗（降級為原順序）
        reranker_succeeded = len(reranked_ids) > 0

    return ApiResponse(data={
        "query": body.query,
        "search_mode": body.search_mode,
        "hit_count": len(hits),
        "reranked": bool(body.reranker) and bool(reranked_ids),
        "rerank_warning": (
            "Reranker 啟用但失敗或不可用，已 fallback 回原排序"
            if body.reranker and not reranked_ids else None
        ),
        "results": [
            {
                "paragraph_id": str(h["id"]),
                "content": h["content"][:300] + ("…" if len(h["content"]) > 300 else ""),
                "doc_name": h["doc_name"],
                "score": round(float(h["score"]), 6),
                "vector_score": round(float(h.get("vector_score", 0.0)), 6),
                "rrf_score": (
                    round(float(h["score"]), 6)
                    if body.search_mode == "hybrid"
                    else None
                ),
                "rerank_score": (
                    round(reranked_ids[str(h["id"])], 6)
                    if str(h["id"]) in reranked_ids
                    else None
                ),
                "title": h.get("title"),
            }
            for h in hits
        ],
    })
