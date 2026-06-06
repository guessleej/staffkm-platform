"""pgvector 向量儲存 + PostgreSQL FTS 混合搜尋 (RRF)"""
import re
import uuid
from typing import Any, Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

# CJK 字符範圍：中文、日文假名（在字符前後插入空格讓 simple 字典逐字索引）
_CJK_RE = re.compile(
    r"([一-鿿㐀-䶿豈-﫿぀-ゟ゠-ヿ])"
)

# v5.13: pgvector 的 ivfflat/hnsw 索引維度上限 = 2000。超過（如 Qwen3-Embedding 4096）只能
#   暴力精確檢索（不建 ANN 索引），語意正確、僅大語料較慢。所有建索引 DDL 一律過此守衛。
ANN_INDEX_MAX_DIM = 2000


def ann_index_supported() -> bool:
    """目前 EMBEDDING_DIMENSION 是否可建 pgvector ANN 索引（≤2000）。"""
    return settings.EMBEDDING_DIMENSION <= ANN_INDEX_MAX_DIM


_PARA_ANN_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_para_embed_vector ON paragraph_embeddings\n"
    "    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);"
    if ann_index_supported()
    else "-- 維度 > 2000：pgvector 無法建 ivfflat/hnsw → 改暴力精確檢索（不建向量索引）"
)

CREATE_VECTOR_TABLE = f"""
CREATE TABLE IF NOT EXISTS paragraph_embeddings (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paragraph_id UUID NOT NULL REFERENCES paragraphs(id) ON DELETE CASCADE,
    kb_id        UUID NOT NULL,
    embedding    vector({settings.EMBEDDING_DIMENSION}),
    created_at   TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uniq_para_embed UNIQUE (paragraph_id)
);
CREATE INDEX IF NOT EXISTS idx_para_embed_kb     ON paragraph_embeddings(kb_id);
{_PARA_ANN_INDEX}
"""


async def set_ivfflat_probes(session: AsyncSession) -> None:
    """在當前 transaction 內套用 ivfflat.probes（SET LOCAL → pooling 安全、commit 即還原）。

    pgvector 預設 probes=1 只掃 1 個倒排清單 → 召回極差、對 embedding 微擾敏感（同 query
    不同 process 可能 0 筆 vs 全中）。值以 int() 內嵌（SET 不吃 bind 參數，int() 防注入）。
    """
    await session.execute(text(f"SET LOCAL ivfflat.probes = {int(settings.IVFFLAT_PROBES)}"))


# ---------------------------------------------------------------------------
# CJK 分字
# ---------------------------------------------------------------------------

def tokenize_for_fts(content: str) -> str:
    """在 CJK 字符之間插入空格，讓 PostgreSQL simple 字典能逐字建立索引。

    例：「台灣請假政策」→「台 灣 請 假 政 策」
    """
    spaced = _CJK_RE.sub(r" \1 ", content)
    return re.sub(r"\s+", " ", spaced).strip()


# ---------------------------------------------------------------------------
# 寫入操作
# ---------------------------------------------------------------------------

async def upsert_embedding(
    session: AsyncSession,
    paragraph_id: uuid.UUID,
    kb_id: uuid.UUID,
    embedding: list[float],
) -> None:
    # v5.13: milvus 模式 → 向量寫 Milvus（pgvector 表不寫，避開維度限制）；否則寫 pgvector
    from app.core import milvus_store
    if milvus_store.is_enabled():
        await milvus_store.upsert(paragraph_id, kb_id, embedding)
        return
    await session.execute(
        text("""
            INSERT INTO paragraph_embeddings (paragraph_id, kb_id, embedding)
            VALUES (:pid, :kb_id, CAST(:emb AS vector))
            ON CONFLICT (paragraph_id) DO UPDATE SET embedding = EXCLUDED.embedding
        """),
        {"pid": str(paragraph_id), "kb_id": str(kb_id), "emb": str(embedding)},
    )


async def update_search_vector(
    session: AsyncSession,
    paragraph_id: uuid.UUID,
    content: str,
) -> None:
    """更新段落的預計算 tsvector（含 CJK 分字）。"""
    tokens = tokenize_for_fts(content)
    await session.execute(
        text("""
            UPDATE paragraphs
            SET search_vector = to_tsvector('simple', :tokens)
            WHERE id = :id
        """),
        {"tokens": tokens, "id": str(paragraph_id)},
    )


# ---------------------------------------------------------------------------
# 混合搜尋（RRF）
# ---------------------------------------------------------------------------

async def hybrid_search(
    session: AsyncSession,
    kb_id: uuid.UUID,
    query_embedding: list[float],
    query_text: str,
    top_k: int = 5,
    similarity_threshold: float = 0.5,
    vector_weight: float = 0.7,
    search_mode: Literal["hybrid", "vector", "fts"] = "hybrid",
    rrf_k: int = 60,
) -> list[dict[str, Any]]:
    """
    混合搜尋：向量相似度 + PostgreSQL Full-Text Search，以 RRF 合併排名。

    search_mode:
        hybrid — 向量 + FTS，RRF 合併（預設）
        vector — 純向量，閾值過濾
        fts    — 純 Full-Text Search
    rrf_k:
        RRF 常數（建議 60），值越大兩路排名的影響越平均
    """
    # v5.13: milvus 模式 → 向量走 Milvus ANN、FTS 留 PG、app 端 RRF 融合（pgvector 表不參與）
    from app.core import milvus_store
    if milvus_store.is_enabled():
        return await _hybrid_search_milvus(
            session, kb_id, query_embedding, query_text, top_k,
            similarity_threshold, vector_weight, search_mode, rrf_k,
        )

    fts_query_tokens = tokenize_for_fts(query_text)
    # 候選集倍數：拉大後再取 top_k，確保 RRF 合併有足夠候選
    candidate_k = min(top_k * 4, 100)
    fw = round(1.0 - vector_weight, 6)

    # 純 FTS 不碰向量索引；其餘模式先拉高 ivfflat.probes 以穩定召回
    if search_mode != "fts":
        await set_ivfflat_probes(session)

    if search_mode == "vector":
        result = await session.execute(
            text("""
                SELECT p.id, p.content, p.title, p.meta, d.name AS doc_name,
                       p.document_id, p.order_index,
                       (1 - (pe.embedding <=> CAST(:emb AS vector))) AS score,
                       (1 - (pe.embedding <=> CAST(:emb AS vector))) AS vector_score
                FROM paragraph_embeddings pe
                JOIN paragraphs p ON p.id = pe.paragraph_id
                JOIN documents  d ON d.id = p.document_id
                WHERE pe.kb_id  = :kb_id
                  AND p.is_active = true
                  AND (1 - (pe.embedding <=> CAST(:emb AS vector))) >= :threshold
                ORDER BY pe.embedding <=> CAST(:emb AS vector)
                LIMIT :top_k
            """),
            {
                "emb": str(query_embedding),
                "kb_id": str(kb_id),
                "threshold": similarity_threshold,
                "top_k": top_k,
            },
        )

    elif search_mode == "fts":
        result = await session.execute(
            text("""
                SELECT p.id, p.content, p.title, p.meta, d.name AS doc_name,
                       p.document_id, p.order_index,
                       ts_rank_cd(p.search_vector,
                                  websearch_to_tsquery('simple', :fts_query)) AS score,
                       0.0::float AS vector_score
                FROM paragraphs p
                JOIN documents d ON d.id = p.document_id
                WHERE p.knowledge_base_id = :kb_id
                  AND p.is_active = true
                  AND p.search_vector IS NOT NULL
                  AND p.search_vector @@ websearch_to_tsquery('simple', :fts_query)
                ORDER BY score DESC
                LIMIT :top_k
            """),
            {
                "fts_query": fts_query_tokens,
                "kb_id": str(kb_id),
                "top_k": top_k,
            },
        )

    else:  # hybrid — RRF
        result = await session.execute(
            text("""
                WITH vector_ranked AS (
                    SELECT
                        pe.paragraph_id,
                        1 - (pe.embedding <=> CAST(:emb AS vector))                    AS vector_score,
                        ROW_NUMBER() OVER (ORDER BY pe.embedding <=> CAST(:emb AS vector)) AS vrank
                    FROM paragraph_embeddings pe
                    WHERE pe.kb_id = :kb_id
                    ORDER BY pe.embedding <=> CAST(:emb AS vector)
                    LIMIT :candidate_k
                ),
                fts_ranked AS (
                    SELECT
                        p.id AS paragraph_id,
                        ROW_NUMBER() OVER (
                            ORDER BY ts_rank_cd(
                                p.search_vector,
                                websearch_to_tsquery('simple', :fts_query)
                            ) DESC
                        ) AS frank
                    FROM paragraphs p
                    WHERE p.knowledge_base_id = :kb_id
                      AND p.is_active = true
                      AND p.search_vector IS NOT NULL
                      AND p.search_vector @@ websearch_to_tsquery('simple', :fts_query)
                    ORDER BY ts_rank_cd(
                        p.search_vector,
                        websearch_to_tsquery('simple', :fts_query)
                    ) DESC
                    LIMIT :candidate_k
                ),
                merged AS (
                    SELECT
                        COALESCE(v.paragraph_id, f.paragraph_id)          AS paragraph_id,
                        COALESCE(v.vector_score, 0.0)                      AS vector_score,
                        -- RRF：排名越前，分數越高；未出現者視為排在最後一名之後
                        (1.0 / (:rrf_k + COALESCE(v.vrank, :candidate_k + 1))) * :vw
                        + (1.0 / (:rrf_k + COALESCE(f.frank, :candidate_k + 1))) * :fw
                                                                           AS rrf_score
                    FROM vector_ranked v
                    FULL OUTER JOIN fts_ranked f ON v.paragraph_id = f.paragraph_id
                )
                SELECT
                    p.id, p.content, p.title, p.meta, d.name AS doc_name,
                    p.document_id, p.order_index,
                    m.rrf_score   AS score,
                    m.vector_score
                FROM merged m
                JOIN paragraphs p ON p.id = m.paragraph_id
                JOIN documents  d ON d.id = p.document_id
                -- v5.12: 補 is_active 濾 — vector_ranked CTE 只用 kb_id 未濾 is_active，
                --   軟刪/停用段落會經向量路徑回傳被引用（FTS 分支已濾、vector-only 漏網）。
                WHERE p.is_active = true
                  AND (
                       (m.vector_score >= :threshold)
                    OR (m.vector_score = 0.0)       -- FTS-only 命中，不受向量閾值限制
                  )
                ORDER BY m.rrf_score DESC
                LIMIT :top_k
            """),
            {
                "emb": str(query_embedding),
                "kb_id": str(kb_id),
                "fts_query": fts_query_tokens,
                "candidate_k": candidate_k,
                "rrf_k": rrf_k,
                "vw": vector_weight,
                "fw": fw,
                "threshold": similarity_threshold,
                "top_k": top_k,
            },
        )

    rows = result.mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# v5.13: Milvus 後端的 hybrid 檢索（向量在 Milvus、FTS 在 PG、Python 端 RRF 融合）
# ---------------------------------------------------------------------------

async def _fts_ranked_ids(
    session: AsyncSession, kb_id: uuid.UUID, fts_query: str, limit: int,
) -> list[str]:
    """PG FTS 取候選 paragraph_id（依 ts_rank_cd 由高到低）。"""
    result = await session.execute(
        text("""
            SELECT p.id AS paragraph_id
            FROM paragraphs p
            WHERE p.knowledge_base_id = :kb_id
              AND p.is_active = true
              AND p.search_vector IS NOT NULL
              AND p.search_vector @@ websearch_to_tsquery('simple', :q)
            ORDER BY ts_rank_cd(p.search_vector,
                                websearch_to_tsquery('simple', :q)) DESC
            LIMIT :lim
        """),
        {"kb_id": str(kb_id), "q": fts_query, "lim": limit},
    )
    return [str(r["paragraph_id"]) for r in result.mappings().all()]


async def _fetch_paragraphs(
    session: AsyncSession, ids: list[str],
) -> dict[str, dict[str, Any]]:
    """依 paragraph_id 取原文/標題/meta/文件名（只取 is_active）。回 {pid: row}。"""
    if not ids:
        return {}
    result = await session.execute(
        text("""
            SELECT p.id, p.content, p.title, p.meta, d.name AS doc_name,
                   p.document_id, p.order_index
            FROM paragraphs p
            JOIN documents d ON d.id = p.document_id
            WHERE p.id = ANY(:ids) AND p.is_active = true
        """),
        {"ids": [uuid.UUID(i) for i in ids]},
    )
    return {str(r["id"]): dict(r) for r in result.mappings().all()}


async def _hybrid_search_milvus(
    session: AsyncSession,
    kb_id: uuid.UUID,
    query_embedding: list[float],
    query_text: str,
    top_k: int,
    similarity_threshold: float,
    vector_weight: float,
    search_mode: str,
    rrf_k: int,
) -> list[dict[str, Any]]:
    from app.core import milvus_store

    candidate_k = min(top_k * 4, 100)
    fw = round(1.0 - vector_weight, 6)
    fts_tokens = tokenize_for_fts(query_text)

    # 向量側（Milvus ANN）：[(pid, cosine_sim)]，已由高到低
    vec_hits = (
        [] if search_mode == "fts"
        else await milvus_store.search(kb_id, query_embedding, candidate_k)
    )
    vec_rank = {pid: i + 1 for i, (pid, _s) in enumerate(vec_hits)}
    vec_score = {pid: s for pid, s in vec_hits}

    # FTS 側（PG）：paragraph_id 依排名
    fts_ids = (
        [] if search_mode == "vector"
        else await _fts_ranked_ids(session, kb_id, fts_tokens, candidate_k)
    )
    fts_rank = {pid: i + 1 for i, pid in enumerate(fts_ids)}

    # 融合
    scored: list[tuple[str, float, float]] = []  # (pid, score, vector_score)
    if search_mode == "vector":
        for pid, s in vec_hits:
            if s >= similarity_threshold:
                scored.append((pid, s, s))
        scored = scored[:top_k]
    elif search_mode == "fts":
        # 純 FTS：以排名倒序當分數（與 pgvector 路徑語意一致：score=ts_rank，這裡用名次近似）
        n = len(fts_ids)
        for i, pid in enumerate(fts_ids[:top_k]):
            scored.append((pid, float(n - i), 0.0))
    else:  # hybrid — RRF（與 pgvector SQL 版同公式）
        for pid in set(vec_rank) | set(fts_rank):
            vs = vec_score.get(pid, 0.0)
            # vector-only 命中需過 cosine 門檻；FTS 有命中者不受限（對齊 SQL 版 m.vector_score=0.0 例外）
            if pid not in fts_rank and vs < similarity_threshold:
                continue
            rrf = (
                (1.0 / (rrf_k + vec_rank.get(pid, candidate_k + 1))) * vector_weight
                + (1.0 / (rrf_k + fts_rank.get(pid, candidate_k + 1))) * fw
            )
            scored.append((pid, rrf, vs))
        scored.sort(key=lambda x: x[1], reverse=True)
        scored = scored[:top_k]

    # 取原文（一次 SQL）。is_active 過濾在此處做 → 軟刪段落即使在 Milvus 也不會被回傳。
    pmap = await _fetch_paragraphs(session, [pid for pid, _, _ in scored])
    out: list[dict[str, Any]] = []
    for pid, score, vscore in scored:
        row = pmap.get(pid)
        if not row:
            continue
        row = dict(row)
        row["score"] = score
        row["vector_score"] = vscore
        out.append(row)
    return out
