"""語意檢索 API — 向量 + PostgreSQL FTS Hybrid Search（RRF）"""
import asyncio
import json
import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.runtime_models import get_active_embedder
from app.config import settings
from app.core.reranker import rerank
from app.core.vectorstore import hybrid_search
from app.models.knowledge_base import KnowledgeBase
from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_core.utils import database as _db
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


async def _docs_matching_tags(
    session: AsyncSession, kb_ids: list[uuid.UUID], tags: list[str], mode: str
) -> set[str] | None:
    """回傳 kb_ids 內、tags 符合的文件 id 集合；tags 空 → None（不過濾）。

    all  → d.tags @> [...]（含全部）；any → jsonb_exists_any（含任一）。
    用 jsonb_exists_any 函式而非 ?| 運算子，避開 SQLAlchemy 對 ? 的 bind 解析衝突。
    """
    if not tags:
        return None
    if mode == "all":
        cond = "d.tags @> CAST(:tags_json AS jsonb)"
        params = {"tags_json": json.dumps(tags)}
    else:  # any
        cond = "jsonb_exists_any(d.tags, :tags_arr)"
        params = {"tags_arr": tags}  # Python list → text[]（CLAUDE.md array bind 紀律）
    rows = await session.execute(
        text(f"SELECT id FROM documents d WHERE d.knowledge_base_id = ANY(:kbs) AND {cond}"),
        {"kbs": [str(k) for k in kb_ids], **params},
    )
    return {str(r[0]) for r in rows.fetchall()}


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


async def _expand_to_parents(session: AsyncSession, hits: list[dict]) -> list[dict]:
    """v5.13 #1 small-to-big：命中的小塊(child)→ 回傳其父塊(parent section)內容，並去重。

    在 rerank/top_k 之後執行（不影響排名）。同一父塊的多個 child 命中只保留排名最前者、置換成
    父塊內容、標 _parent_expanded（後續 context_window 不再對它開窗）。child 無 parent_id（既有
    資料 / 關閉時入庫）→ 原樣保留，行為與舊版一致。
    """
    pids = {str(h["parent_id"]) for h in hits if h.get("parent_id")}
    if not pids:
        return hits
    rows = await session.execute(
        text("SELECT id, content FROM paragraph_parents WHERE id = ANY(:ids)"),
        {"ids": [uuid.UUID(p) for p in pids]},
    )
    pmap = {str(r["id"]): r["content"] for r in rows.mappings().all()}
    out: list[dict] = []
    seen: set[str] = set()
    for h in hits:
        pid = str(h["parent_id"]) if h.get("parent_id") else None
        if pid and pid in pmap:
            if pid in seen:
                continue  # 同一父塊只回一次（去重，避免重複內容塞爆 context）
            seen.add(pid)
            h = dict(h)
            h["content"] = pmap[pid]
            h["_parent_expanded"] = True
        out.append(h)
    return out


# RFC-014：graph 召回融合（RRF 第三路）抽到 app.core.fusion（純邏輯、可輕量 CI 單測）
from app.core.fusion import _fuse_graph_results  # noqa: E402


async def _graph_enabled_kbs(session: AsyncSession, kb_ids: list) -> list:
    """回傳 kb_ids 中 graph_enabled=true 的；皆否回空（→ 不跑 graph 召回）。"""
    if not kb_ids:
        return []
    rows = await session.execute(
        text("SELECT id FROM knowledge_bases WHERE id = ANY(:ids) AND graph_enabled = true"),
        {"ids": [str(k) for k in kb_ids]},
    )
    return [r[0] for r in rows.fetchall()]


async def _score_paragraphs_by_ids(
    session: AsyncSession, pids: list, query_embedding: list[float]
) -> list[dict]:
    """把 graph 找到的 paragraph_id 取回（含向量分數），shape 同 hybrid_search 以便融合。"""
    if not pids:
        return []
    rows = await session.execute(
        text("""
            SELECT p.id, p.content, p.title, p.meta, d.name AS doc_name,
                   p.document_id, p.order_index, p.parent_id,
                   (1 - (pe.embedding <=> CAST(:emb AS vector))) AS score,
                   (1 - (pe.embedding <=> CAST(:emb AS vector))) AS vector_score
            FROM paragraphs p
            JOIN paragraph_embeddings pe ON pe.paragraph_id = p.id
            JOIN documents d ON d.id = p.document_id
            WHERE p.id = ANY(:pids) AND p.is_active = true
        """),
        {"pids": [str(x) for x in pids], "emb": str(query_embedding)},
    )
    return [dict(r) for r in rows.mappings().all()]


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
    # P2 上下文窗口召回（small-to-big）：命中段落額外帶回同文件前後 N 段（0=關閉）。
    #   v5.13 **預設 1**：小塊精準命中、回傳時帶回鄰段給 LLM 更完整上下文（答案品質↑、成本極低）。
    context_window: int = Field(default=1, ge=0, le=5, description="每個命中段落額外帶回同文件前後 N 段的內容")
    # P3 tag 過濾：限定命中段落所屬文件需符合 tags（any=任一/all=全部）
    tags: list[str] = Field(default_factory=list, description="文件標籤過濾；空=不過濾")
    tag_match_mode: Literal["any", "all"] = Field(default="any", description="any=符合任一標籤；all=需符合全部")
    # v5.13 多查詢：LLM 改寫成多個等價查詢各自檢索 → RRF 融合（None=用系統預設 QUERY_EXPAND_ENABLED）
    multi_query: bool | None = Field(default=None, description="查詢改寫/多查詢融合；None=系統預設")


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
    # v5.13 多查詢：非 fts 模式且啟用時，LLM 把 query 改寫成多個等價變體，各自嵌入後分別檢索再 RRF 融合
    query_embedding: list[float] = []
    query_variants: list[str] = [body.query]
    variant_embeddings: list[list[float]] = []
    if body.search_mode != "fts":
        embedder = await get_active_embedder(session)
        _do_multi = settings.QUERY_EXPAND_ENABLED if body.multi_query is None else body.multi_query
        if _do_multi:
            from app.core.query_transform import expand_query
            query_variants = await expand_query(body.query)
        variant_embeddings = await embedder.embed_batch(query_variants)
        query_embedding = variant_embeddings[0]  # 原查詢向量（graph 錨定/單查詢都用它）

    # v5.12: 內建 reranker 預設啟用時也要多撈候選給它重排（不只 body.reranker 才撈）
    _will_rerank = bool(body.reranker) or settings.RERANKER_DEFAULT_LOCAL
    fetch_k = body.retrieval_top_k if _will_rerank else body.top_k

    # P3 tag 過濾：先算出符合標籤的文件集合；有過濾時多撈候選避免 top_k 不足
    tag_doc_ids = await _docs_matching_tags(
        session, allowed_kb_ids, body.tags, body.tag_match_mode
    )
    if tag_doc_ids is not None:
        if not tag_doc_ids:  # 沒有任何文件符合標籤 → 直接空結果
            return ApiResponse(data=SearchResponse(citations=[], total=0, search_mode=body.search_mode))
        fetch_k = max(fetch_k, 50)

    async def _search_kb(s: AsyncSession, kb_id) -> list[dict]:
        # 單查詢（未展開）：直接走原路徑，零額外開銷、行為與既有一致
        if len(query_variants) <= 1:
            return await hybrid_search(
                session=s, kb_id=kb_id,
                query_embedding=query_embedding, query_text=body.query,
                top_k=fetch_k, similarity_threshold=body.similarity_threshold,
                vector_weight=body.vector_weight, search_mode=body.search_mode, rrf_k=body.rrf_k,
            )
        # 多查詢：每個變體各自檢索 → RRF 融合（fuse_multi_query 純邏輯、可單測）
        from app.core.fusion import fuse_multi_query
        lists = []
        for qt, qe in zip(query_variants, variant_embeddings):
            lists.append(await hybrid_search(
                session=s, kb_id=kb_id,
                query_embedding=qe, query_text=qt,
                top_k=fetch_k, similarity_threshold=body.similarity_threshold,
                vector_weight=body.vector_weight, search_mode=body.search_mode, rrf_k=body.rrf_k,
            ))
        return fuse_multi_query(lists, fetch_k, body.rrf_k)

    all_results: list[dict] = []
    if len(allowed_kb_ids) <= 1 or _db._session_factory is None:
        # 單 KB（最常見）走注入 session，免開新連線
        for kb_id in allowed_kb_ids:
            all_results.extend(await _search_kb(session, kb_id))
    else:
        # v5.12: 多 KB 並發 — 原本逐 KB 序列化、延遲線性放大。asyncpg 同連線不可並發 →
        #   各 KB 開獨立 session；semaphore 限流避免打穿連線池。
        sem = asyncio.Semaphore(5)

        async def _one(kb_id):
            async with sem:
                async with _db._session_factory() as s:
                    return await _search_kb(s, kb_id)

        per_kb = await asyncio.gather(*[_one(k) for k in allowed_kb_ids])
        for hits in per_kb:
            all_results.extend(hits)

    # RFC-014 GraphRAG（MVP）：實體錨定召回 → RRF 第三路融合（僅 graph_enabled 的 KB；查詢時零 LLM）
    if query_embedding:
        graph_kbs = await _graph_enabled_kbs(session, allowed_kb_ids)
        if graph_kbs:
            from app.core.graph import graph_anchored_paragraph_ids
            g_pids = await graph_anchored_paragraph_ids(
                session, graph_kbs, query_embedding, settings.GRAPH_QUERY_TOP_ENTITIES
            )
            g_rows = await _score_paragraphs_by_ids(session, g_pids, query_embedding)
            # graph-only 候選須通過與 hybrid 向量同一條相關門檻（similarity_threshold）才併入
            _fuse_graph_results(all_results, g_rows, body.rrf_k, body.similarity_threshold)

    # 跨知識庫去重（依分數降序）
    seen: set[str] = set()
    deduped: list[dict] = []
    for r in sorted(all_results, key=lambda x: x["score"], reverse=True):
        pid = str(r["id"])
        if pid not in seen:
            seen.add(pid)
            deduped.append(r)

    # P3 tag 過濾：只保留所屬文件符合標籤的命中（rerank 前，確保排名/取數在過濾後的集合上）
    if tag_doc_ids is not None:
        deduped = [r for r in deduped if str(r.get("document_id")) in tag_doc_ids]

    # Reranker 重排：請求未帶 reranker → fallback 系統預設（system_settings.default.rerank）
    #   → 再 fallback 內建 in-process reranker（v5.12 default-on）。
    reranker_config = body.reranker
    if not reranker_config:
        from app.core.runtime_models import resolve_reranker
        reranker_config = await resolve_reranker(session)
    if not reranker_config and settings.RERANKER_DEFAULT_LOCAL:
        reranker_config = {"type": "local", "model_name": settings.RERANKER_LOCAL_MODEL}
    if reranker_config:
        deduped = await rerank(
            query=body.query,
            documents=deduped,
            reranker_config=reranker_config,
            top_n=body.rerank_top_n,
        )
        final_results = deduped
    else:
        final_results = deduped[: body.top_k]

    # v5.13 #1 small-to-big：命中小塊 → 回傳整個父塊（去重）。預設開；無 parent_id 的命中原樣保留。
    if settings.SMALL_TO_BIG_ENABLED:
        final_results = await _expand_to_parents(session, final_results)
    # P2 上下文窗口：只對「未被父塊取代」的命中開窗（父塊已涵蓋完整上下文，避免重複）
    if body.context_window > 0:
        todo = [h for h in final_results if not h.get("_parent_expanded")]
        if todo:
            await _expand_context(session, todo, body.context_window)

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
