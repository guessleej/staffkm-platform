"""Reranker 整合 — 支援 Cohere、自訂 HTTP endpoint"""
import httpx
import structlog

log = structlog.get_logger()


async def rerank(
    query: str,
    documents: list[dict],  # 每個有 content, doc_name 等欄位
    reranker_config: dict,   # {type, api_key, base_url, model_name, top_n}
    top_n: int = 5,
) -> list[dict]:
    """
    對 documents 重新排序並回傳前 top_n 個。
    若 reranker_config 為空或失敗，直接回傳原始 documents[:top_n]。
    """
    if not reranker_config or not documents:
        return documents[:top_n]

    reranker_type = reranker_config.get("type", "http")

    try:
        if reranker_type == "cohere":
            return await _rerank_cohere(query, documents, reranker_config, top_n)
        else:  # 通用 HTTP endpoint（相容 Cohere API 格式、BGE-Reranker 等）
            return await _rerank_http(query, documents, reranker_config, top_n)
    except Exception as e:
        log.warning("reranker_failed", error=str(e), fallback="original_order")
        return documents[:top_n]


async def _rerank_cohere(query, documents, config, top_n):
    """呼叫 Cohere Rerank v2 API"""
    api_key = config.get("api_key", "")
    model = config.get("model_name", "rerank-multilingual-v3.0")
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://api.cohere.com/v2/rerank",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "query": query,
                "documents": [d["content"] for d in documents],
                "top_n": top_n,
            },
        )
        resp.raise_for_status()
        results = resp.json()["results"]
        return [documents[r["index"]] for r in results]


async def _rerank_http(query, documents, config, top_n):
    """通用 HTTP reranker（相容 Cohere API 格式）"""
    base_url = config.get("base_url", "").rstrip("/")
    api_key = config.get("api_key", "")
    model = config.get("model_name", "bge-reranker-v2-m3")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{base_url}/rerank",
            headers=headers,
            json={
                "model": model,
                "query": query,
                "documents": [d["content"] for d in documents],
                "top_n": top_n,
            },
        )
        resp.raise_for_status()
        results = resp.json()["results"]
        return [documents[r["index"]] for r in results]
