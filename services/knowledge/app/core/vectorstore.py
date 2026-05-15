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

CREATE_VECTOR_TABLE = """
CREATE TABLE IF NOT EXISTS paragraph_embeddings (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paragraph_id UUID NOT NULL REFERENCES paragraphs(id) ON DELETE CASCADE,
    kb_id        UUID NOT NULL,
    embedding    vector({dim}),
    created_at   TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uniq_para_embed UNIQUE (paragraph_id)
);
CREATE INDEX IF NOT EXISTS idx_para_embed_kb     ON paragraph_embeddings(kb_id);
CREATE INDEX IF NOT EXISTS idx_para_embed_vector ON paragraph_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
""".format(
    dim=settings.EMBEDDING_DIMENSION
)


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
    await session.execute(
        text("""
            INSERT INTO paragraph_embeddings (paragraph_id, kb_id, embedding)
            VALUES (:pid, :kb_id, :emb::vector)
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
    fts_query_tokens = tokenize_for_fts(query_text)
    # 候選集倍數：拉大後再取 top_k，確保 RRF 合併有足夠候選
    candidate_k = min(top_k * 4, 100)
    fw = round(1.0 - vector_weight, 6)

    if search_mode == "vector":
        result = await session.execute(
            text("""
                SELECT p.id, p.content, p.title, p.meta, d.name AS doc_name,
                       (1 - (pe.embedding <=> :emb::vector)) AS score,
                       (1 - (pe.embedding <=> :emb::vector)) AS vector_score
                FROM paragraph_embeddings pe
                JOIN paragraphs p ON p.id = pe.paragraph_id
                JOIN documents  d ON d.id = p.document_id
                WHERE pe.kb_id  = :kb_id
                  AND p.is_active = true
                  AND (1 - (pe.embedding <=> :emb::vector)) >= :threshold
                ORDER BY pe.embedding <=> :emb::vector
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
                        1 - (pe.embedding <=> :emb::vector)                    AS vector_score,
                        ROW_NUMBER() OVER (ORDER BY pe.embedding <=> :emb::vector) AS vrank
                    FROM paragraph_embeddings pe
                    WHERE pe.kb_id = :kb_id
                    ORDER BY pe.embedding <=> :emb::vector
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
                    m.rrf_score   AS score,
                    m.vector_score
                FROM merged m
                JOIN paragraphs p ON p.id = m.paragraph_id
                JOIN documents  d ON d.id = p.document_id
                -- 純向量命中但相似度低於閾值，且未被 FTS 收錄者予以過濾
                WHERE (m.vector_score >= :threshold)
                   OR (m.vector_score = 0.0)       -- FTS-only 命中，不受向量閾值限制
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
