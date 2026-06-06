"""v5.13: Milvus 向量後端（VECTOR_BACKEND=milvus 時啟用）。

為什麼：pgvector 的 ivfflat/hnsw 索引維度上限 2000；高維 embedding（如 Qwen3-Embedding 4096）
在 pgvector 只能暴力全掃，不專業。Milvus 無 2000 維限制、原生 HNSW/IVF 索引 → 高維 + 真索引兼得。

設計：
- 只存「向量 + 主鍵(paragraph_id) + kb_id 純量」於 Milvus；段落原文 / FTS 仍在 Postgres。
  → hybrid 檢索 = Milvus 向量 ANN ＋ PG FTS，app 端 RRF 融合（見 vectorstore.hybrid_search）。
- pymilvus 是同步 client → 一律包進 asyncio.to_thread，不阻塞 event loop。
- COSINE metric：Milvus 回的 distance 即 cosine 相似度（-1..1，越大越相似），對齊 staffKM vector_score。
"""
import asyncio

import structlog

from app.config import settings

log = structlog.get_logger()

_client = None
_collection_ready = False


def _get_client():
    global _client
    if _client is None:
        from pymilvus import MilvusClient
        _client = MilvusClient(uri=settings.MILVUS_URI, token=settings.MILVUS_TOKEN or "")
    return _client


def _ensure_collection_sync() -> None:
    """建 collection（若無）：主鍵 paragraph_id + kb_id 純量 + embedding 向量 + HNSW(COSINE) 索引。"""
    global _collection_ready
    if _collection_ready:
        return
    from pymilvus import DataType

    c = _get_client()
    name = settings.MILVUS_COLLECTION
    if not c.has_collection(name):
        schema = c.create_schema(auto_id=False, enable_dynamic_field=False)
        schema.add_field("paragraph_id", DataType.VARCHAR, is_primary=True, max_length=64)
        schema.add_field("kb_id", DataType.VARCHAR, max_length=64)
        schema.add_field("embedding", DataType.FLOAT_VECTOR, dim=settings.EMBEDDING_DIMENSION)
        index_params = c.prepare_index_params()
        index_params.add_index(
            field_name="kb_id", index_type="INVERTED",   # 純量過濾用
        )
        index_params.add_index(
            field_name="embedding",
            index_type="HNSW",
            metric_type="COSINE",
            params={"M": 16, "efConstruction": 200},
        )
        c.create_collection(name, schema=schema, index_params=index_params)
        log.info("milvus_collection_created", name=name, dim=settings.EMBEDDING_DIMENSION)
    c.load_collection(name)
    _collection_ready = True


async def ensure_collection() -> None:
    await asyncio.to_thread(_ensure_collection_sync)


async def upsert(paragraph_id, kb_id, embedding: list[float]) -> None:
    def _do():
        _ensure_collection_sync()
        _get_client().upsert(settings.MILVUS_COLLECTION, [{
            "paragraph_id": str(paragraph_id),
            "kb_id": str(kb_id),
            "embedding": embedding,
        }])
    await asyncio.to_thread(_do)


async def delete_by_paragraph(paragraph_id) -> None:
    def _do():
        _get_client().delete(settings.MILVUS_COLLECTION,
                             filter=f'paragraph_id == "{paragraph_id}"')
    await asyncio.to_thread(_do)


async def delete_by_kb(kb_id) -> None:
    def _do():
        _get_client().delete(settings.MILVUS_COLLECTION, filter=f'kb_id == "{kb_id}"')
    await asyncio.to_thread(_do)


async def search(kb_id, query_embedding: list[float], top_k: int) -> list[tuple[str, float]]:
    """回 [(paragraph_id, cosine_similarity)]，依相似度由高到低。"""
    def _do():
        _ensure_collection_sync()
        res = _get_client().search(
            settings.MILVUS_COLLECTION,
            data=[query_embedding],
            limit=top_k,
            filter=f'kb_id == "{kb_id}"',
            output_fields=["paragraph_id"],
            search_params={"metric_type": "COSINE", "params": {"ef": max(64, top_k * 4)}},
        )
        out = []
        for hit in (res[0] if res else []):
            pid = hit.get("entity", {}).get("paragraph_id") or hit.get("id")
            out.append((str(pid), float(hit.get("distance", 0.0))))
        return out
    return await asyncio.to_thread(_do)


def is_enabled() -> bool:
    return (settings.VECTOR_BACKEND or "pgvector").lower() == "milvus"
