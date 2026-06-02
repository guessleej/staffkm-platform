"""v5.13: 地端 ASR（語音轉文字）— faster-whisper（CTranslate2，無雲端、資料不出境）。

- 用於「音檔/影片音軌進知識庫」：把語音轉成帶時間碼的逐字稿 → 走既有 chunk/embed 管線。
- **地端優先**（符合公文/政府資料主權賣點）：模型在本機推論，音軌不送任何雲端。
- VAD（語音活動偵測）內建切段 → 長音檔自動分段、回每段 {start, end, text} 時間碼。
- 記憶體防呆：faster-whisper medium 載入吃 ~2GB；容器上限不足 → 跳過 + 明確 log（同 reranker 模式），
  不讓它 OOM-SIGKILL 整個 worker。要啟用需把 knowledge-worker 記憶體上限調 ≥4g。
- 模型快取固定 /app/.whisper_cache；首次用到才下載（~1.5GB，需網路一次）。要完全離線可 build 時預載。
"""
import os
import tempfile

import structlog

from app.config import settings

log = structlog.get_logger()

_CACHE_DIR = "/app/.whisper_cache"
_model = None
_load_failed = False

# faster-whisper medium(int8) 載入峰值約 ~2GB；保險要求容器記憶體上限 ≥ 約 3GB。
# 低於此載入易 OOM（SIGKILL，try/except 抓不到）→ 啟動就擋、給明確 log。
_ASR_MIN_LIMIT_BYTES = 3_000_000_000


def _cgroup_mem_limit_bytes():
    """讀容器記憶體上限（cgroup v2 / v1）。無限制或讀不到回 None。"""
    for path in ("/sys/fs/cgroup/memory.max",                    # cgroup v2
                 "/sys/fs/cgroup/memory/memory.limit_in_bytes"):  # cgroup v1
        try:
            with open(path) as f:
                raw = f.read().strip()
        except (FileNotFoundError, OSError):
            continue
        if raw in ("", "max"):
            return None
        try:
            val = int(raw)
        except ValueError:
            continue
        if val >= (1 << 62):
            return None
        return val
    return None


def memory_guard():
    """檢查容器記憶體上限是否足以載入 ASR 模型。回 (ok: bool, detail: str)。"""
    limit = _cgroup_mem_limit_bytes()
    if limit is None:
        return True, "no container memory limit detected"
    gib = limit / (1024 ** 3)
    if limit < _ASR_MIN_LIMIT_BYTES:
        return False, (
            f"container memory limit {gib:.2f}GiB is below the ~3GiB needed to load "
            f"faster-whisper '{settings.ASR_MODEL}' — raise knowledge-worker memory to >=4g "
            f"(compose: services.knowledge-worker … memory: 4g) or use a smaller ASR_MODEL"
        )
    return True, f"container memory limit {gib:.2f}GiB ok"


def is_available() -> bool:
    """記憶體足夠且尚未載入失敗 → 視為可用（給上傳端點先擋掉，避免收了音檔卻轉不了）。"""
    ok, _ = memory_guard()
    return ok and not _load_failed


def _get_model():
    """懶載入單例。第一次轉錄時載入模型（首次會下載 ~1.5GB），之後常駐。"""
    global _model, _load_failed
    if _model is not None or _load_failed:
        return _model
    ok, detail = memory_guard()
    if not ok:
        log.error("asr_disabled_insufficient_memory", reason=detail)
        _load_failed = True
        return None
    try:
        from faster_whisper import WhisperModel
        os.makedirs(_CACHE_DIR, exist_ok=True)
        _model = WhisperModel(
            settings.ASR_MODEL,
            device=settings.ASR_DEVICE,
            compute_type=settings.ASR_COMPUTE_TYPE,
            download_root=_CACHE_DIR,
        )
        log.info("asr_model_loaded", model=settings.ASR_MODEL, device=settings.ASR_DEVICE)
    except Exception as e:  # noqa: BLE001
        log.error("asr_init_failed", error=str(e)[:300])
        _load_failed = True
        _model = None
    return _model


def transcribe(audio_bytes: bytes) -> list[dict]:
    """音檔 bytes → 帶時間碼的逐字稿段落 [{start, end, text}, ...]。

    - 任何 ffmpeg 解得開的格式皆可（mp3/wav/m4a/flac/ogg…；faster-whisper 內建 PyAV 解碼）。
    - VAD 內建切段：長音檔自動分段，回每段時間碼。
    - 模型不可用（記憶體不足/載入失敗）→ raise RuntimeError（讓上層把文件標 error 並回明確訊息）。
    """
    model = _get_model()
    if model is None:
        raise RuntimeError(
            "地端 ASR 不可用：knowledge-worker 記憶體不足（需 ≥4g）或模型載入失敗。"
            "請調高記憶體上限，或改用字幕檔（.srt/.vtt）上傳。"
        )
    # faster-whisper 透過檔案路徑解碼最穩 → 落到暫存檔
    with tempfile.NamedTemporaryFile(suffix=".media", delete=True) as tmp:
        tmp.write(audio_bytes)
        tmp.flush()
        language = settings.ASR_LANGUAGE or None   # 空字串 → None（自動偵測）
        segments, _info = model.transcribe(
            tmp.name,
            language=language,
            vad_filter=True,              # 語音活動偵測：自動跳過靜音、切段
            beam_size=settings.ASR_BEAM_SIZE,
        )
        out: list[dict] = []
        for seg in segments:              # segments 是 generator，逐段串流出來
            text = (seg.text or "").strip()
            if text:
                out.append({"start": float(seg.start), "end": float(seg.end), "text": text})
    log.info("asr_transcribed", segments=len(out))
    return out
