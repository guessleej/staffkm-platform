"""Reranker 整合 — 支援 Cohere、自訂 HTTP endpoint、Ollama（fallback embedding cosine）"""
import math

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
    成功時每個 doc 上會塞 `relevance_score` 欄位。
    若 reranker_config 為空或失敗，直接回傳原始 documents[:top_n]。
    """
    if not reranker_config or not documents:
        return documents[:top_n]

    reranker_type = (reranker_config.get("type") or "http").lower()

    try:
        if reranker_type == "local":
            # v5.12: 內建 in-process ONNX cross-encoder（fastembed，無外部服務）
            from app.core.local_reranker import rerank_local
            return await rerank_local(query, documents, top_n)
        elif reranker_type == "cohere":
            return await _rerank_cohere(query, documents, reranker_config, top_n)
        elif reranker_type == "ollama":
            return await _rerank_ollama(query, documents, reranker_config, top_n)
        elif reranker_type == "cross_encoder":
            return await _rerank_cross_encoder(query, documents, reranker_config, top_n)
        else:  # 通用 HTTP endpoint（相容 Cohere API 格式、BGE-Reranker 等）
            return await _rerank_http(query, documents, reranker_config, top_n)
    except NotImplementedError as e:
        log.warning("reranker_not_implemented", type=reranker_type, error=str(e))
        return documents[:top_n]
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
        out: list[dict] = []
        for r in results:
            doc = dict(documents[r["index"]])
            doc["relevance_score"] = float(r.get("relevance_score", 0.0))
            out.append(doc)
        return out


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
        out: list[dict] = []
        for r in results:
            doc = dict(documents[r["index"]])
            doc["relevance_score"] = float(
                r.get("relevance_score", r.get("score", 0.0))
            )
            out.append(doc)
        return out


async def _rerank_cross_encoder(query, documents, config, top_n):
    """呼叫 staffkm-reranker container（v3.4 P3）。

    config 必須帶 endpoint (預設 http://reranker:8000)。
    每個 doc 的 content 抽 text 送 model；回 indices+scores 後重排 documents。
    """
    endpoint = config.get("endpoint", "http://reranker:8000").rstrip("/")
    doc_texts = [d.get("content", "") if isinstance(d, dict) else str(d) for d in documents]
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{endpoint}/rerank",
                json={"query": query, "documents": doc_texts, "top_n": top_n},
            )
            r.raise_for_status()
            result = r.json()
    except Exception as e:
        log.warning("cross_encoder_rerank_failed", error=str(e), fallback="original_order")
        return documents[:top_n]

    indices = result.get("indices", [])
    scores  = result.get("scores", [])
    ranked: list[dict] = []
    for i, idx in enumerate(indices):
        if 0 <= idx < len(documents):
            doc = documents[idx]
            if isinstance(doc, dict):
                doc = dict(doc)
                doc["relevance_score"] = float(scores[i]) if i < len(scores) else None
            ranked.append(doc)
    return ranked


async def _rerank_ollama(query, documents, config, top_n):
    """Ollama 沒有原生 cross-encoder rerank API（截至 v3.3）。

    策略：
      1. 先嘗試呼叫 Ollama 的 `/api/rerank`（v0.x 部分 fork 已實作；若 404 直接 fallback）
      2. fallback：用 embedding model 對 query 與每個 doc 各算 embedding，計算
         cosine similarity 作為 rerank score。效果通常比 cross-encoder 差但無外部依賴。
         可在 v3.4 換成真正的 cross-encoder。
    """
    base_url = (config.get("base_url") or "http://embedder:11434").rstrip("/")
    model = config.get("model_name") or "bge-reranker-v2-m3"
    embed_model = config.get("embed_model") or "snowflake-arctic-embed2"

    # 路徑 1：嘗試 Ollama 原生 rerank（多數版本沒有，預期 404）
    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            resp = await client.post(
                f"{base_url}/api/rerank",
                json={
                    "model": model,
                    "query": query,
                    "documents": [d["content"] for d in documents],
                    "top_n": top_n,
                },
            )
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                out: list[dict] = []
                for r in results:
                    doc = dict(documents[r["index"]])
                    doc["relevance_score"] = float(
                        r.get("relevance_score", r.get("score", 0.0))
                    )
                    out.append(doc)
                if out:
                    return out
            # 404 / 其他都當作不支援，跳 fallback
        except httpx.HTTPError as e:
            log.info("ollama_native_rerank_unavailable", error=str(e))

        # 路徑 2：embedding cosine fallback
        async def _embed(text: str) -> list[float]:
            r = await client.post(
                f"{base_url}/api/embeddings",
                json={"model": embed_model, "prompt": text},
            )
            r.raise_for_status()
            data = r.json()
            return list(data.get("embedding") or [])

        q_emb = await _embed(query)
        if not q_emb:
            raise NotImplementedError(
                "ollama embedding 回傳空，無法 fallback rerank（請改用 cohere 或 http 型別）"
            )

        scored: list[tuple[int, float]] = []
        for i, doc in enumerate(documents):
            try:
                d_emb = await _embed(doc["content"][:2000])
            except Exception:
                d_emb = []
            scored.append((i, _cosine(q_emb, d_emb)))

        scored.sort(key=lambda x: x[1], reverse=True)
        out: list[dict] = []
        for idx, score in scored[:top_n]:
            doc = dict(documents[idx])
            doc["relevance_score"] = float(score)
            out.append(doc)
        return out


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
