"""執行期模型解析 — 把 admin/models 頁設定的 system_settings.default.* 接到 runtime。

- vision OCR：resolve_vision_ocr（default.vision）
- reranker：resolve_reranker（default.rerank）
- LLM（default.llm）：agent 服務的 base_agent.resolve_system_llm
- embedding：resolve_embedding —— **讀 embedding.active（重嵌 job 套用、與既有向量一致的模型），
  非 default.embedding**。query 模型必須與索引模型一致，否則向量空間不符、檢索全錯。
  切換流程：UI 存 default.embedding（desired）→ admin 觸發 reindex job → 全庫重嵌 +（維度不符時）
  遷移共用 vector 欄 → 成功後寫 embedding.active → runtime 起用新模型。
"""
from __future__ import annotations

import base64
import json

import structlog
from sqlalchemy import text

from app.config import settings
from app.core.embedder import get_embedder

log = structlog.get_logger()


async def resolve_embedding(session) -> tuple[str, str, str | None]:
    """回 (model, api_key, base_url)。優先 embedding.active（與既有向量一致），否則 env 後備。"""
    env = (settings.EMBEDDING_MODEL, settings.OPENAI_API_KEY, settings.EMBEDDING_BASE_URL or None)
    try:
        row = (await session.execute(
            text("SELECT value FROM system_settings WHERE key = 'embedding.active'")
        )).fetchone()
        if not row or row.value in (None, "", '""'):
            return env
        raw = row.value
        if isinstance(raw, str):
            raw = json.loads(raw)
        if not isinstance(raw, dict) or not raw.get("model"):
            return env
        return (
            raw["model"],
            raw.get("api_key") or settings.OPENAI_API_KEY,
            raw.get("base_url") or settings.EMBEDDING_BASE_URL or None,
        )
    except Exception as e:  # noqa: BLE001 — 解析失敗一律 fallback env（不可讓檢索整個壞掉）
        log.warning("resolve_embedding_failed", error=str(e))
        return env


async def get_active_embedder(session):
    """取得「目前語料實際使用的」embedding service（與索引一致）。所有 ingest/query 用這個。"""
    model, api_key, base_url = await resolve_embedding(session)
    return get_embedder(model, api_key, base_url)


def _normalize_openai_base(base: str | None) -> str | None:
    """OpenAI 相容端點需 /v1；ollama 原生 base_url（給 verify 用）沒帶 → 補上。"""
    if not base:
        return base
    b = base.rstrip("/")
    return b if b.endswith("/v1") else b + "/v1"


async def resolve_vision_ocr(session) -> dict:
    """讀 system_settings.default.vision → 解出 vision OCR 模型 + provider 連線設定。

    回傳可直接展開給 DocumentProcessor(**cfg) 的 dict：
      {ocr_engine, vision_model, vision_base_url, vision_api_key}
    未設定 default.vision 時回 {}（DocumentProcessor 沿用 env settings）。
    """
    try:
        row = (await session.execute(text(
            "SELECT value FROM system_settings WHERE key = 'default.vision'"
        ))).fetchone()
        if not row or row.value in (None, "", '""'):
            return {}
        raw = row.value
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:  # noqa: BLE001
                pass
        model_name = raw if isinstance(raw, str) else (
            raw.get("model_name") if isinstance(raw, dict) else None
        )
        if not model_name:
            return {}

        prov = (await session.execute(text("""
            SELECT p.provider_type, p.base_url, p.api_key_enc
            FROM ai_models m JOIN model_providers p ON p.id = m.provider_id
            WHERE m.model_name = :mn AND m.model_type = 'vision' AND m.status = 'active'
            ORDER BY m.is_default DESC
            LIMIT 1
        """), {"mn": model_name})).fetchone()

        base_url = _normalize_openai_base(prov.base_url) if prov else None
        api_key = None
        if prov and prov.api_key_enc:
            try:
                api_key = base64.b64decode(prov.api_key_enc.encode()).decode()
            except Exception:  # noqa: BLE001
                api_key = None

        # 使用者明確選了 img2Txt 模型 → 啟用 vision 引擎（覆寫預設 tesseract）
        return {
            "ocr_engine": "vision",
            "vision_model": model_name,
            "vision_base_url": base_url,
            "vision_api_key": api_key,
        }
    except Exception as e:  # noqa: BLE001 — DB 問題不致命，回空 → fallback env
        log.warning("resolve_vision_ocr_failed", error=str(e))
        return {}


# provider_type → reranker.rerank() 的 type 欄位
_RERANK_TYPE_BY_PROVIDER = {
    "cohere": "cohere",
    "ollama": "ollama",
}


async def _read_default_model_name(session, key: str) -> str | None:
    """讀 system_settings[key] 的模型名（jsonb 字串或 {model_name}）。"""
    row = (await session.execute(text(
        "SELECT value FROM system_settings WHERE key = :k"
    ), {"k": key})).fetchone()
    if not row or row.value in (None, "", '""'):
        return None
    raw = row.value
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:  # noqa: BLE001
            pass
    return raw if isinstance(raw, str) else (
        raw.get("model_name") if isinstance(raw, dict) else None
    )


async def resolve_reranker(session) -> dict | None:
    """讀 system_settings.default.rerank → 組 reranker.rerank() 用的 config。

    回傳 {type, base_url, api_key, model_name}；未設定 default.rerank 回 None
    （search 維持「不重排」行為）。rerank 走 /rerank 或 /api/rerank，故 base_url
    **不補 /v1**（與 OpenAI 相容端點不同）。
    """
    try:
        model_name = await _read_default_model_name(session, "default.rerank")
        if not model_name:
            return None
        prov = (await session.execute(text("""
            SELECT p.provider_type, p.base_url, p.api_key_enc
            FROM ai_models m JOIN model_providers p ON p.id = m.provider_id
            WHERE m.model_name = :mn AND m.model_type = 'reranker' AND m.status = 'active'
            ORDER BY m.is_default DESC
            LIMIT 1
        """), {"mn": model_name})).fetchone()

        provider_type = prov.provider_type if prov else ""
        base_url = (prov.base_url.rstrip("/") if prov and prov.base_url else None)
        api_key = None
        if prov and prov.api_key_enc:
            try:
                api_key = base64.b64decode(prov.api_key_enc.encode()).decode()
            except Exception:  # noqa: BLE001
                api_key = None

        return {
            "type": _RERANK_TYPE_BY_PROVIDER.get(provider_type, "http"),
            "base_url": base_url,
            "api_key": api_key,
            "model_name": model_name,
        }
    except Exception as e:  # noqa: BLE001
        log.warning("resolve_reranker_failed", error=str(e))
        return None
