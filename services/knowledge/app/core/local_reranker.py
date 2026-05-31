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

# bge-reranker-base 載入峰值約 ~1.9GB；加上服務本身 → 容器記憶體上限需 ~2.3GB 以上才安全。
# 低於此值載入必 OOM（SIGKILL，try/except 抓不到）→ 啟動就擋掉、給明確 log，不讓它無限重啟。
_RERANKER_MIN_LIMIT_BYTES = 2_500_000_000


def _cgroup_mem_limit_bytes():
    """讀容器記憶體上限（cgroup v2 / v1）。無限制或讀不到回 None。"""
    for path in ("/sys/fs/cgroup/memory.max",                    # cgroup v2
                 "/sys/fs/cgroup/memory/memory.limit_in_bytes"):  # cgroup v1
        try:
            with open(path) as f:
                raw = f.read().strip()
        except (FileNotFoundError, OSError):
            continue
        if raw in ("", "max"):          # v2 無限制
            return None
        try:
            val = int(raw)
        except ValueError:
            continue
        if val >= (1 << 62):            # v1 無限制哨兵值（極大）
            return None
        return val
    return None


def memory_guard():
    """檢查容器記憶體上限是否足以載入 reranker。回 (ok: bool, detail: str)。"""
    limit = _cgroup_mem_limit_bytes()
    if limit is None:
        return True, "no container memory limit detected"
    gib = limit / (1024 ** 3)
    if limit < _RERANKER_MIN_LIMIT_BYTES:
        return False, (
            f"container memory limit {gib:.2f}GiB is below the ~2.3GiB needed to load "
            f"bge-reranker-base — raise the knowledge container memory limit to >=3g "
            f"(compose: services.knowledge … memory: 3g) or set RERANKER_DEFAULT_LOCAL=false"
        )
    return True, f"container memory limit {gib:.2f}GiB ok"


def _get_encoder():
    """懶載入單例。第一次呼叫（或 warmup）時載入模型，之後常駐。"""
    global _encoder, _load_failed
    if _encoder is not None or _load_failed:
        return _encoder
    # 記憶體防呆：上限不足就別載（否則 OOM 直接 SIGKILL 整個行程 → 無限重啟）。
    ok, detail = memory_guard()
    if not ok:
        log.error("local_reranker_disabled_insufficient_memory", reason=detail)
        _load_failed = True
        return None
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
