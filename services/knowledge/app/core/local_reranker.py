"""v5.12: 內建 in-process ONNX cross-encoder reranker。

- 用 fastembed（ONNX runtime，**不依賴 torch**、無外部服務）→ 直接打包進 staffKM 出貨。
- default-on：knowledge 服務啟動時 warmup 預載，檢索時自動套用。
- 預設模型 BAAI/bge-reranker-v2-m3（Apache-2.0、多語含繁中）；載入失敗自動退到較小的
  BAAI/bge-reranker-base，再失敗則退回「不重排」（不致命）。
- 模型快取固定在 /app/.fastembed_cache（Dockerfile build 時預先下載 → 離線可用）。
"""
import asyncio
import structlog

from app.config import settings

log = structlog.get_logger()

_CACHE_DIR = "/app/.fastembed_cache"
_encoder = None
_load_failed = False


def _get_encoder():
    """懶載入單例。第一次呼叫（或 warmup）時載入模型，之後常駐。"""
    global _encoder, _load_failed
    if _encoder is not None or _load_failed:
        return _encoder
    try:
        from fastembed.rerank.cross_encoder import TextCrossEncoder
        name = settings.RERANKER_LOCAL_MODEL or "BAAI/bge-reranker-base"
        try:
            _encoder = TextCrossEncoder(model_name=name, cache_dir=_CACHE_DIR)
            log.info("local_reranker_loaded", model=name)
        except Exception as e:  # noqa: BLE001
            log.warning("local_reranker_model_fallback", model=name, error=str(e)[:200])
            _encoder = TextCrossEncoder(model_name="BAAI/bge-reranker-base", cache_dir=_CACHE_DIR)
            log.info("local_reranker_loaded", model="BAAI/bge-reranker-base")
    except Exception as e:  # noqa: BLE001
        log.error("local_reranker_init_failed", error=str(e)[:300])
        _load_failed = True
        _encoder = None
    return _encoder


def warmup() -> bool:
    """啟動時預載（安裝即啟用）。回傳是否成功；失敗不阻斷服務啟動。"""
    return _get_encoder() is not None


async def rerank_local(query: str, documents: list[dict], top_n: int) -> list[dict]:
    """對 documents 用 cross-encoder 重排，回前 top_n（每個塞 relevance_score）。
    模型未就緒 → 回原順序前 top_n（degrade 不致命）。"""
    enc = _get_encoder()
    if enc is None or not documents:
        return documents[:top_n]
    texts = [d.get("content", "") if isinstance(d, dict) else str(d) for d in documents]
    # fastembed rerank 是同步 CPU 計算 → 丟 threadpool，不阻塞 event loop
    scores = await asyncio.get_event_loop().run_in_executor(
        None, lambda: list(enc.rerank(query, texts))
    )
    ranked = sorted(zip(documents, scores), key=lambda z: z[1], reverse=True)
    out: list[dict] = []
    for d, s in ranked[:top_n]:
        dd = dict(d)
        dd["relevance_score"] = float(s)
        out.append(dd)
    return out
