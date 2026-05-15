"""命中測試 API — 測試查詢在知識庫的檢索效果"""
import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.embedder import get_embedder
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
        embedder = get_embedder(
            settings.EMBEDDING_MODEL,
            settings.OPENAI_API_KEY,
            settings.EMBEDDING_BASE_URL or None,
        )
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

    return ApiResponse(data={
        "query": body.query,
        "search_mode": body.search_mode,
        "hit_count": len(hits),
        "results": [
            {
                "paragraph_id": str(h["id"]),
                "content": h["content"][:300] + ("…" if len(h["content"]) > 300 else ""),
                "doc_name": h["doc_name"],
                "score": round(float(h["score"]), 6),
                "vector_score": round(float(h.get("vector_score", 0.0)), 6),
                "title": h.get("title"),
            }
            for h in hits
        ],
    })
