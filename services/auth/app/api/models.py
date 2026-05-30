"""模型供應商與 AI 模型管理 API（管理員用）"""
import uuid
import httpx
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, delete, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse, PagedResponse, PageMeta
from staffkm_core.secrets import decrypt_secret, encrypt_secret
from staffkm_core.utils.database import get_session

router = APIRouter()


# v5.9.2: provider 建立後自動 seed 的 default models（auth 服務獨立持有，
# 跟 agent/app/data/model_pricing.py PROVIDER_DEFAULT_MODELS 保持同步）
_DEFAULT_MODELS_ON_CREATE: dict[str, list[tuple[str, str, str]]] = {
    "openai": [
        ("gpt-4o",                  "llm",       "GPT-4o"),
        ("gpt-4o-mini",             "llm",       "GPT-4o mini"),
        ("gpt-4-turbo",             "llm",       "GPT-4 Turbo"),
        ("gpt-3.5-turbo",           "llm",       "GPT-3.5 Turbo"),
        ("o1-preview",              "llm",       "o1-preview"),
        ("o1-mini",                 "llm",       "o1-mini"),
        ("text-embedding-3-small",  "embedding", "Embedding 3 small"),
        ("text-embedding-3-large",  "embedding", "Embedding 3 large"),
        ("dall-e-3",                "image",     "DALL·E 3"),
        ("whisper-1",               "stt",       "Whisper"),
        ("tts-1",                   "tts",       "TTS-1"),
    ],
    "anthropic": [
        ("claude-3-5-sonnet-20241022", "llm", "Claude 3.5 Sonnet"),
        ("claude-3-5-haiku-20241022",  "llm", "Claude 3.5 Haiku"),
    ],
    # v5.12: registry type 是 gemini（非 google）→ 種子 key 對齊，否則建 gemini provider 種不到
    "gemini": [
        ("gemini-2.0-flash",   "llm",       "Gemini 2.0 Flash"),
        ("gemini-1.5-pro",     "llm",       "Gemini 1.5 Pro"),
        ("gemini-1.5-flash",   "llm",       "Gemini 1.5 Flash"),
        ("text-embedding-004", "embedding", "Gemini Embedding 004"),
    ],
    # ollama 不寫死 — 模型清單由 list_provider_models 即時打 /api/tags 動態同步。
    "cohere": [
        ("command-r-plus",          "llm",      "Command R+"),
        ("rerank-multilingual-v3.0","reranker", "Rerank multilingual v3"),
    ],
    # ── v5.12 scope B：非 openai_compat / 特殊 API → 種精選預設清單（保證「加了就有模型」）──
    # gemini/azure/deepgram/elevenlabs/stability 另疊 live-fetch（見 _sync_special_provider_models）；
    # vertex/bedrock 需雲端 SDK/OAuth、voyage/jina 無公開 list endpoint → 僅種子。
    "azure_openai": [
        ("gpt-4o",                 "llm",       "GPT-4o (Azure 部署名請依實際調整)"),
        ("gpt-4o-mini",            "llm",       "GPT-4o mini (Azure)"),
        ("text-embedding-3-large", "embedding", "Embedding 3 large (Azure)"),
    ],
    "vertex_ai": [
        ("gemini-1.5-pro",     "llm",       "Gemini 1.5 Pro (Vertex)"),
        ("gemini-1.5-flash",   "llm",       "Gemini 1.5 Flash (Vertex)"),
        ("text-embedding-005", "embedding", "Vertex Embedding 005"),
    ],
    "bedrock": [
        ("anthropic.claude-3-5-sonnet-20241022-v2:0", "llm",       "Claude 3.5 Sonnet (Bedrock)"),
        ("anthropic.claude-3-5-haiku-20241022-v1:0",  "llm",       "Claude 3.5 Haiku (Bedrock)"),
        ("amazon.titan-embed-text-v2:0",              "embedding", "Titan Embed v2 (Bedrock)"),
        ("meta.llama3-1-70b-instruct-v1:0",           "llm",       "Llama 3.1 70B (Bedrock)"),
    ],
    "deepgram": [
        ("nova-3", "stt", "Deepgram Nova-3"),
        ("nova-2", "stt", "Deepgram Nova-2"),
    ],
    "elevenlabs": [
        ("eleven_multilingual_v2", "tts", "Multilingual v2"),
        ("eleven_turbo_v2_5",      "tts", "Turbo v2.5"),
        ("eleven_flash_v2_5",      "tts", "Flash v2.5"),
    ],
    "stability_ai": [
        ("stable-diffusion-3.5-large", "image", "SD 3.5 Large"),
        ("sd3.5-medium",               "image", "SD 3.5 Medium"),
        ("stable-image-core",          "image", "Stable Image Core"),
    ],
    "voyage": [
        ("voyage-3",      "embedding", "Voyage 3"),
        ("voyage-3-lite", "embedding", "Voyage 3 Lite"),
        ("rerank-2",      "reranker",  "Voyage Rerank 2"),
    ],
    "jina": [
        ("jina-embeddings-v3",                   "embedding", "Jina Embeddings v3"),
        ("jina-reranker-v2-base-multilingual",   "reranker",  "Jina Reranker v2"),
    ],
    "moonshot": [
        ("kimi-k2.6",                       "llm",    "Kimi K2.6 (旗艦)"),
        ("kimi-k2.5",                       "llm",    "Kimi K2.5"),
        ("moonshot-v1-8k",                  "llm",    "Moonshot v1 8K"),
        ("moonshot-v1-32k",                 "llm",    "Moonshot v1 32K"),
        ("moonshot-v1-128k",                "llm",    "Moonshot v1 128K"),
        ("moonshot-v1-auto",                "llm",    "Moonshot v1 Auto"),
        ("moonshot-v1-8k-vision-preview",   "vision", "Moonshot v1 8K Vision"),
        ("moonshot-v1-32k-vision-preview",  "vision", "Moonshot v1 32K Vision"),
        ("moonshot-v1-128k-vision-preview", "vision", "Moonshot v1 128K Vision"),
    ],
    "groq": [
        ("llama-3.1-70b-versatile", "llm", "Llama 3.1 70B (Groq)"),
        ("llama-3.1-8b-instant",    "llm", "Llama 3.1 8B (Groq)"),
    ],
    "mistral": [
        ("mistral-large-latest", "llm", "Mistral Large"),
        ("mistral-small-latest", "llm", "Mistral Small"),
    ],
    "openrouter": [
        ("openai/gpt-4o",               "llm", "GPT-4o (via OpenRouter)"),
        ("anthropic/claude-3.5-sonnet", "llm", "Claude 3.5 Sonnet (via OpenRouter)"),
    ],
    "xai": [("grok-beta", "llm", "Grok Beta")],
}


async def _seed_default_models(session, provider_id: str, provider_type: str) -> int:
    """v5.9.2: provider 建立後自動補 default model 列。
    用 ON CONFLICT DO NOTHING（依賴 alembic 0021 加的 UNIQUE INDEX）"""
    from sqlalchemy import text
    defaults = _DEFAULT_MODELS_ON_CREATE.get(provider_type, [])
    if not defaults:
        return 0
    inserted = 0
    for name, mtype, display in defaults:
        r = await session.execute(text("""
            INSERT INTO ai_models (provider_id, model_name, model_type, display_name, status, is_default, config)
            VALUES (CAST(:pid AS uuid), CAST(:n AS varchar), CAST(:t AS varchar), CAST(:d AS varchar), 'active', FALSE, '{}'::jsonb)
            ON CONFLICT (provider_id, model_name) DO NOTHING
        """), {"pid": provider_id, "n": name, "t": mtype, "d": display})
        inserted += r.rowcount or 0
    return inserted

# ---------------------------------------------------------------------------
# 輔助函式 — API Key 混淆（base64）
# ---------------------------------------------------------------------------

def _encode_api_key(plain: str) -> str:
    """加密 API Key（統一走 staffkm_core.secrets：金鑰有設→fernet:、無→plain:）。"""
    return encrypt_secret(plain) or ""


def _decode_api_key(encoded: str) -> str:
    """解密 API Key（fernet:/plain:/legacy-base64 皆可，向後相容舊 base64）。"""
    return decrypt_secret(encoded) or ""


def _mask_api_key(encoded: str) -> str:
    """回傳 API Key 前綴（解碼後取前 8 字元）並遮罩其餘部分。"""
    try:
        plain = _decode_api_key(encoded)
        if len(plain) <= 8:
            return plain[:3] + "***"
        return plain[:8] + "***"
    except Exception:
        return "***"


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class ProviderCreate(BaseModel):
    name: str
    provider_type: str  # openai / ollama / azure / anthropic / custom
    base_url: str | None = None
    api_key: str | None = None
    config: dict[str, Any] | None = None


class ProviderUpdate(BaseModel):
    name: str | None = None
    provider_type: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    status: str | None = None
    config: dict[str, Any] | None = None


class ProviderOut(BaseModel):
    id: uuid.UUID
    name: str
    provider_type: str
    base_url: str | None
    api_key_prefix: str | None  # 遮罩後的前綴
    status: str
    config: dict[str, Any] | None
    tenant_id: str | None
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    updated_by: str | None


class ModelCreate(BaseModel):
    model_name: str
    model_type: str  # llm / embedding / reranker / tts / stt
    display_name: str | None = None
    config: dict[str, Any] | None = None
    is_default: bool = False


class ModelUpdate(BaseModel):
    model_name: str | None = None
    model_type: str | None = None
    display_name: str | None = None
    config: dict[str, Any] | None = None
    is_default: bool | None = None
    status: str | None = None


class ModelOut(BaseModel):
    id: uuid.UUID
    provider_id: uuid.UUID
    model_name: str
    model_type: str
    display_name: str | None
    config: dict[str, Any] | None
    is_default: bool
    status: str
    price_per_1k_input_usd: float | None = None
    price_per_1k_output_usd: float | None = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# 輔助 — 從原始 Row mapping 建立 ProviderOut
# ---------------------------------------------------------------------------

def _row_to_provider_out(row: Any) -> ProviderOut:
    api_key_prefix = _mask_api_key(row.api_key_enc) if row.api_key_enc else None
    return ProviderOut(
        id=row.id,
        name=row.name,
        provider_type=row.provider_type,
        base_url=row.base_url,
        api_key_prefix=api_key_prefix,
        status=row.status,
        config=row.config,
        tenant_id=row.tenant_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        created_by=row.created_by,
        updated_by=row.updated_by,
    )


def _row_to_model_out(row: Any) -> ModelOut:
    pin = getattr(row, "price_per_1k_input_usd", None)
    pout = getattr(row, "price_per_1k_output_usd", None)
    return ModelOut(
        id=row.id,
        provider_id=row.provider_id,
        model_name=row.model_name,
        model_type=row.model_type,
        display_name=row.display_name,
        config=row.config,
        is_default=row.is_default,
        status=row.status,
        price_per_1k_input_usd=float(pin) if pin is not None else None,
        price_per_1k_output_usd=float(pout) if pout is not None else None,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# ---------------------------------------------------------------------------
# Provider 端點
# ---------------------------------------------------------------------------

@router.get("/providers", response_model=PagedResponse[ProviderOut], summary="列出所有模型供應商")
async def list_providers(
    page: int = 1,
    page_size: int = 20,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    offset = (page - 1) * page_size

    from sqlalchemy import text
    count_result = await session.execute(text("SELECT COUNT(*) FROM model_providers"))
    total: int = count_result.scalar() or 0

    rows_result = await session.execute(
        text(
            "SELECT id, name, provider_type, base_url, api_key_enc, status, config, "
            "tenant_id, created_at, updated_at, created_by, updated_by "
            "FROM model_providers ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        ),
        {"limit": page_size, "offset": offset},
    )
    rows = rows_result.fetchall()

    data = [_row_to_provider_out(r) for r in rows]
    return PagedResponse(
        data=data,
        meta=PageMeta(page=page, page_size=page_size, total=total, total_pages=-(-total // page_size)),
    )


@router.post("/providers", response_model=ApiResponse[ProviderOut], summary="建立模型供應商", status_code=201)
async def create_provider(
    body: ProviderCreate,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    from sqlalchemy import text

    provider_id = uuid.uuid4()
    tenant_id = getattr(request.state, "tenant_id", None) if request else None
    created_by = getattr(request.state, "user_id", None) if request else None
    api_key_enc = _encode_api_key(body.api_key) if body.api_key else None

    import json
    # config column 是 NOT NULL DEFAULT '{}'，所以 None 改成 '{}' 明確帶
    config_json = json.dumps(body.config) if body.config else '{}'

    await session.execute(
        text(
            "INSERT INTO model_providers (id, name, provider_type, base_url, api_key_enc, "
            "status, config, tenant_id, created_by, updated_by) "
            "VALUES (:id, :name, :provider_type, :base_url, :api_key_enc, "
            "'active', CAST(:config AS jsonb), :tenant_id, :created_by, :updated_by)"
        ),
        {
            "id": str(provider_id),
            "name": body.name,
            "provider_type": body.provider_type,
            "base_url": body.base_url,
            "api_key_enc": api_key_enc,
            "config": config_json,
            "tenant_id": tenant_id,
            "created_by": created_by,
            "updated_by": created_by,
        },
    )

    # v5.9.2: provider 建立後立刻 seed default model 列，避免 admin UI 顯示空模型
    # 之前只有 agent startup pricing_seed 會跑 → user 刪掉舊 provider 重建（新 id）
    # 就拿不到 default models，要等下次 agent 重啟才有
    try:
        seeded = await _seed_default_models(session, str(provider_id), body.provider_type)
    except Exception as exc:
        # seed 失敗不致命，記 log 不擋 create 回應
        import structlog
        structlog.get_logger().warning("default_model_seed_failed", error=str(exc), provider_type=body.provider_type)
        seeded = 0

    row_result = await session.execute(
        text(
            "SELECT id, name, provider_type, base_url, api_key_enc, status, config, "
            "tenant_id, created_at, updated_at, created_by, updated_by "
            "FROM model_providers WHERE id = :id"
        ),
        {"id": str(provider_id)},
    )
    row = row_result.fetchone()
    msg = f"模型供應商建立成功（已預設 {seeded} 個模型）" if seeded else "模型供應商建立成功"
    return ApiResponse(data=_row_to_provider_out(row), message=msg)


@router.get("/providers/{provider_id}", response_model=ApiResponse[ProviderOut], summary="取得供應商詳情")
async def get_provider(
    provider_id: uuid.UUID,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    from sqlalchemy import text

    row_result = await session.execute(
        text(
            "SELECT id, name, provider_type, base_url, api_key_enc, status, config, "
            "tenant_id, created_at, updated_at, created_by, updated_by "
            "FROM model_providers WHERE id = :id"
        ),
        {"id": str(provider_id)},
    )
    row = row_result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="供應商不存在")
    return ApiResponse(data=_row_to_provider_out(row))


@router.put("/providers/{provider_id}", response_model=ApiResponse[ProviderOut], summary="更新供應商")
async def update_provider(
    provider_id: uuid.UUID,
    body: ProviderUpdate,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    from sqlalchemy import text
    import json

    # 確認存在
    exist = await session.execute(
        text("SELECT id FROM model_providers WHERE id = :id"),
        {"id": str(provider_id)},
    )
    if not exist.fetchone():
        raise HTTPException(status_code=404, detail="供應商不存在")

    # 動態建立 SET 子句
    updates: list[str] = []
    params: dict[str, Any] = {"id": str(provider_id)}
    updated_by = getattr(request.state, "user_id", None) if request else None

    if body.name is not None:
        updates.append("name = :name")
        params["name"] = body.name
    if body.provider_type is not None:
        updates.append("provider_type = :provider_type")
        params["provider_type"] = body.provider_type
    if body.base_url is not None:
        updates.append("base_url = :base_url")
        params["base_url"] = body.base_url
    if body.api_key is not None:
        updates.append("api_key_enc = :api_key_enc")
        params["api_key_enc"] = _encode_api_key(body.api_key)
    if body.status is not None:
        updates.append("status = :status")
        params["status"] = body.status
    if body.config is not None:
        updates.append("config = CAST(:config AS jsonb)")
        params["config"] = json.dumps(body.config)

    updates.append("updated_at = NOW()")
    updates.append("updated_by = :updated_by")
    params["updated_by"] = updated_by

    await session.execute(
        text(f"UPDATE model_providers SET {', '.join(updates)} WHERE id = :id"),
        params,
    )

    row_result = await session.execute(
        text(
            "SELECT id, name, provider_type, base_url, api_key_enc, status, config, "
            "tenant_id, created_at, updated_at, created_by, updated_by "
            "FROM model_providers WHERE id = :id"
        ),
        {"id": str(provider_id)},
    )
    row = row_result.fetchone()
    return ApiResponse(data=_row_to_provider_out(row), message="供應商更新成功")


@router.delete("/providers/{provider_id}", response_model=ApiResponse, summary="刪除供應商")
async def delete_provider(
    provider_id: uuid.UUID,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    from sqlalchemy import text

    # v5.12: 顯式刪該 provider 的 ai_models — 不依賴 FK ON DELETE CASCADE。
    #   部分舊部署的 ai_models→model_providers FK 無 cascade（或缺 FK），只刪 provider 會留下
    #   孤兒模型列，殘留在「設定預設模型」清單。先刪子列再刪父列，與同交易一起 commit。
    await session.execute(
        text("DELETE FROM ai_models WHERE provider_id = :id"),
        {"id": str(provider_id)},
    )
    result = await session.execute(
        text("DELETE FROM model_providers WHERE id = :id RETURNING id"),
        {"id": str(provider_id)},
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="供應商不存在")
    return ApiResponse(message="供應商已刪除")


@router.post("/providers/{provider_id}/verify", response_model=ApiResponse, summary="驗證供應商連線")
async def verify_provider(
    provider_id: uuid.UUID,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    from sqlalchemy import text

    row_result = await session.execute(
        text(
            "SELECT provider_type, base_url, api_key_enc, config "
            "FROM model_providers WHERE id = :id"
        ),
        {"id": str(provider_id)},
    )
    row = row_result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="供應商不存在")

    provider_type = row.provider_type
    base_url = row.base_url
    api_key_enc = row.api_key_enc
    api_key = _decode_api_key(api_key_enc) if api_key_enc else None

    ok, detail = await _verify_connection(provider_type, base_url, api_key)
    if not ok:
        raise HTTPException(status_code=422, detail=f"連線驗證失敗：{detail}")
    return ApiResponse(message=f"連線驗證成功：{detail}")


# ---------------------------------------------------------------------------
# AI Model 端點
# ---------------------------------------------------------------------------

@router.get("/providers/{provider_id}/models", response_model=PagedResponse[ModelOut], summary="列出供應商的模型")
async def list_provider_models(
    provider_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    from sqlalchemy import text

    # 確認供應商存在，並取得 type / base_url（自架伺服器要即時同步真實模型）
    exist = await session.execute(
        text("SELECT id, provider_type, base_url, api_key_enc FROM model_providers WHERE id = :id"),
        {"id": str(provider_id)},
    )
    prov = exist.fetchone()
    if not prov:
        raise HTTPException(status_code=404, detail="供應商不存在")

    # 動態同步伺服器上「實際存在」的模型（多了補、少了刪），不寫死任何模型名。
    # 失敗（伺服器沒開）時靜默略過，沿用 DB 既有清單。
    #  - ollama：原生 /api/tags
    #  - 所有 OpenAI 相容（雲端 + 自架）：/v1/models（v5.12 scope A 擴大；抓不到 → 保留 DB 既有）
    if prov.provider_type == "ollama":
        await _sync_ollama_models(session, str(provider_id), prov.base_url)
    elif prov.provider_type in _OPENAI_COMPAT_DEFAULT_BASE:
        api_key = decrypt_secret(prov.api_key_enc) or "" if prov.api_key_enc else ""
        # 雲端 provider 沒填 base_url → 用 registry 預設（如 together → api.together.xyz/v1）
        base = prov.base_url or _OPENAI_COMPAT_DEFAULT_BASE[prov.provider_type]
        await _sync_openai_compat_models(session, str(provider_id), base, api_key)
    elif prov.provider_type in _SPECIAL_LIST_FETCH:
        # v5.12 scope B：gemini/azure/deepgram/elevenlabs/stability best-effort live-fetch
        # （ADD-only、不刪 seeded；無 key/失敗 → 沿用建立時種的預設清單）
        api_key = decrypt_secret(prov.api_key_enc) or "" if prov.api_key_enc else ""
        await _sync_special_provider_models(
            session, str(provider_id), prov.provider_type, prov.base_url, api_key)

    offset = (page - 1) * page_size
    count_result = await session.execute(
        text("SELECT COUNT(*) FROM ai_models WHERE provider_id = :provider_id"),
        {"provider_id": str(provider_id)},
    )
    total: int = count_result.scalar() or 0

    rows_result = await session.execute(
        text(
            "SELECT id, provider_id, model_name, model_type, display_name, config, "
            "is_default, status, price_per_1k_input_usd, price_per_1k_output_usd, "
            "created_at, updated_at "
            "FROM ai_models WHERE provider_id = :provider_id "
            "ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        ),
        {"provider_id": str(provider_id), "limit": page_size, "offset": offset},
    )
    rows = rows_result.fetchall()
    data = [_row_to_model_out(r) for r in rows]
    return PagedResponse(
        data=data,
        meta=PageMeta(page=page, page_size=page_size, total=total, total_pages=-(-total // page_size)),
    )


@router.post("/providers/{provider_id}/models", response_model=ApiResponse[ModelOut], summary="新增模型定義", status_code=201)
async def create_model(
    provider_id: uuid.UUID,
    body: ModelCreate,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    from sqlalchemy import text
    import json

    # 確認供應商存在
    exist = await session.execute(
        text("SELECT id FROM model_providers WHERE id = :id"),
        {"id": str(provider_id)},
    )
    if not exist.fetchone():
        raise HTTPException(status_code=404, detail="供應商不存在")

    model_id = uuid.uuid4()
    # ai_models.config 也是 NOT NULL DEFAULT '{}'
    config_json = json.dumps(body.config) if body.config else '{}'

    # 若設為預設，先取消同類型的其他預設
    if body.is_default:
        await session.execute(
            text(
                "UPDATE ai_models SET is_default = FALSE "
                "WHERE provider_id = :provider_id AND model_type = :model_type"
            ),
            {"provider_id": str(provider_id), "model_type": body.model_type},
        )

    await session.execute(
        text(
            "INSERT INTO ai_models (id, provider_id, model_name, model_type, display_name, "
            "config, is_default, status) "
            "VALUES (:id, :provider_id, :model_name, :model_type, :display_name, "
            "CAST(:config AS jsonb), :is_default, 'active')"
        ),
        {
            "id": str(model_id),
            "provider_id": str(provider_id),
            "model_name": body.model_name,
            "model_type": body.model_type,
            "display_name": body.display_name or body.model_name,
            "config": config_json,
            "is_default": body.is_default,
        },
    )

    row_result = await session.execute(
        text(
            "SELECT id, provider_id, model_name, model_type, display_name, config, "
            "is_default, status, price_per_1k_input_usd, price_per_1k_output_usd, "
            "created_at, updated_at "
            "FROM ai_models WHERE id = :id"
        ),
        {"id": str(model_id)},
    )
    row = row_result.fetchone()
    return ApiResponse(data=_row_to_model_out(row), message="模型定義建立成功")


@router.put("/models/{model_id}", response_model=ApiResponse[ModelOut], summary="更新模型定義")
async def update_model(
    model_id: uuid.UUID,
    body: ModelUpdate,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    from sqlalchemy import text
    import json

    exist_result = await session.execute(
        text("SELECT id, provider_id, model_type FROM ai_models WHERE id = :id"),
        {"id": str(model_id)},
    )
    existing = exist_result.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="模型不存在")

    # 若設為預設，先取消同供應商同類型的其他預設
    target_type = body.model_type or existing.model_type
    if body.is_default:
        await session.execute(
            text(
                "UPDATE ai_models SET is_default = FALSE "
                "WHERE provider_id = :provider_id AND model_type = :model_type AND id != :id"
            ),
            {"provider_id": str(existing.provider_id), "model_type": target_type, "id": str(model_id)},
        )

    updates: list[str] = []
    params: dict[str, Any] = {"id": str(model_id)}

    if body.model_name is not None:
        updates.append("model_name = :model_name")
        params["model_name"] = body.model_name
    if body.model_type is not None:
        updates.append("model_type = :model_type")
        params["model_type"] = body.model_type
    if body.display_name is not None:
        updates.append("display_name = :display_name")
        params["display_name"] = body.display_name
    if body.config is not None:
        updates.append("config = CAST(:config AS jsonb)")
        params["config"] = json.dumps(body.config)
    if body.is_default is not None:
        updates.append("is_default = :is_default")
        params["is_default"] = body.is_default
    if body.status is not None:
        updates.append("status = :status")
        params["status"] = body.status

    updates.append("updated_at = NOW()")

    if updates:
        await session.execute(
            text(f"UPDATE ai_models SET {', '.join(updates)} WHERE id = :id"),
            params,
        )

    row_result = await session.execute(
        text(
            "SELECT id, provider_id, model_name, model_type, display_name, config, "
            "is_default, status, price_per_1k_input_usd, price_per_1k_output_usd, "
            "created_at, updated_at "
            "FROM ai_models WHERE id = :id"
        ),
        {"id": str(model_id)},
    )
    row = row_result.fetchone()
    return ApiResponse(data=_row_to_model_out(row), message="模型更新成功")


@router.delete("/models/{model_id}", response_model=ApiResponse, summary="刪除模型定義")
async def delete_model(
    model_id: uuid.UUID,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    from sqlalchemy import text

    result = await session.execute(
        text("DELETE FROM ai_models WHERE id = :id RETURNING id"),
        {"id": str(model_id)},
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="模型不存在")
    return ApiResponse(message="模型已刪除")


@router.get("/models", response_model=PagedResponse[ModelOut], summary="列出所有模型（可依類型篩選）")
async def list_all_models(
    model_type: str | None = Query(None, description="llm / embedding / reranker / tts / stt"),
    page: int = 1,
    page_size: int = 50,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    from sqlalchemy import text

    offset = (page - 1) * page_size

    if model_type:
        count_result = await session.execute(
            text("SELECT COUNT(*) FROM ai_models WHERE model_type = :model_type"),
            {"model_type": model_type},
        )
        total: int = count_result.scalar() or 0
        rows_result = await session.execute(
            text(
                "SELECT id, provider_id, model_name, model_type, display_name, config, "
                "is_default, status, created_at, updated_at "
                "FROM ai_models WHERE model_type = :model_type "
                "ORDER BY is_default DESC, created_at DESC LIMIT :limit OFFSET :offset"
            ),
            {"model_type": model_type, "limit": page_size, "offset": offset},
        )
    else:
        count_result = await session.execute(text("SELECT COUNT(*) FROM ai_models"))
        total = count_result.scalar() or 0
        rows_result = await session.execute(
            text(
                "SELECT id, provider_id, model_name, model_type, display_name, config, "
                "is_default, status, created_at, updated_at "
                "FROM ai_models ORDER BY model_type, is_default DESC, created_at DESC "
                "LIMIT :limit OFFSET :offset"
            ),
            {"limit": page_size, "offset": offset},
        )

    rows = rows_result.fetchall()
    data = [_row_to_model_out(r) for r in rows]
    return PagedResponse(
        data=data,
        meta=PageMeta(page=page, page_size=page_size, total=total, total_pages=-(-total // page_size)),
    )


# ---------------------------------------------------------------------------
# 私有輔助函式
# ---------------------------------------------------------------------------

def _guess_ollama_model_type(name: str, family: str = "") -> str:
    """從模型名稱/family 推測 model_type（不寫死特定模型，靠關鍵字判斷）。"""
    low = f"{name} {family}".lower()
    if any(k in low for k in ("embed", "bge-m3", "nomic-embed", "bert")):
        return "embedding"
    if "rerank" in low:
        return "reranker"
    if any(k in low for k in ("ocr", "vision", "-vl", "llava", "vl-", "minicpm-v")):
        return "vision"
    return "llm"


async def _sync_ollama_models(session: AsyncSession, provider_id: str, base_url: str | None) -> None:
    """打 ollama /api/tags，把伺服器上實際存在的模型同步進 ai_models。

    - 多了：INSERT（ON CONFLICT DO NOTHING）
    - 少了：DELETE（DB 有但伺服器已無）— ollama 模型一定列在 /api/tags，
      不在清單上的等於抓不到，移除以反映現況
    - is_default：若預設模型仍存在則保留；不存在則一併移除（合理，模型已不在）
    伺服器不可達時靜默 return，不動 DB。
    """
    from sqlalchemy import text
    url = (base_url or "http://localhost:11434").rstrip("/")
    # base_url 可能帶 /v1（OpenAI 相容用），原生 tags 不需要 → 去掉
    if url.endswith("/v1"):
        url = url[:-3]
    url += "/api/tags"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0)) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            return
        payload = resp.json()
    except Exception as exc:  # noqa: BLE001 — 伺服器沒開不致命
        import structlog
        structlog.get_logger().info("ollama_tags_sync_skipped", error=str(exc), url=url)
        return

    live: dict[str, str] = {}  # model_name -> model_type
    for m in payload.get("models", []) or []:
        name = m.get("name") or m.get("model")
        if not name:
            continue
        family = (m.get("details") or {}).get("family", "")
        live[name] = _guess_ollama_model_type(name, family)
    if not live:
        return

    # 補：伺服器有、DB 沒有的
    for name, mtype in live.items():
        await session.execute(text("""
            INSERT INTO ai_models (provider_id, model_name, model_type, display_name, status, is_default, config)
            VALUES (CAST(:pid AS uuid), CAST(:n AS varchar), CAST(:t AS varchar), CAST(:d AS varchar), 'active', FALSE, '{}'::jsonb)
            ON CONFLICT (provider_id, model_name) DO NOTHING
        """), {"pid": provider_id, "n": name, "t": mtype, "d": name})

    # 刪：DB 有、伺服器已無的（用 Python list bind + ANY，避免 PG literal 雷）
    await session.execute(text("""
        DELETE FROM ai_models
        WHERE provider_id = CAST(:pid AS uuid)
          AND model_name <> ALL(:keep)
    """), {"pid": provider_id, "keep": list(live.keys())})
    await session.commit()


# OpenAI 相容 provider 的預設 base_url（單一來源 — verify 與 /v1/models 動態同步共用）。
# v5.12（scope A）：模型清單動態同步從「只有 5 個自架 type」擴大到**所有 openai_compat type**
# （這份 dict 的 keys）。任何有 base_url + api_key 的 openai 相容 provider 都會即時打
# /v1/models 抓真實模型清單（抓不到/401 → graceful、保留 DB 既有 seeded 清單）。
# ⚠ 這份是 auth 服務內「哪些 type 走 /v1/models」的唯一權威；新增 openai_compat provider
#   一律加進這裡（別再分散成多份清單 → 漂移）。非 openai_compat（anthropic/azure/gemini/
#   vertex/bedrock + 特殊 API deepgram/elevenlabs/stability/voyage/jina）走各自路徑（B 隨後）。
_OPENAI_COMPAT_DEFAULT_BASE: dict[str, str] = {
    "openai":       "https://api.openai.com/v1",
    "custom":       "",  # 必須 user 自填
    "moonshot":     "https://api.moonshot.ai/v1",
    "groq":         "https://api.groq.com/openai/v1",
    "together":     "https://api.together.xyz/v1",
    "mistral":      "https://api.mistral.ai/v1",
    "perplexity":   "https://api.perplexity.ai",
    "openrouter":   "https://openrouter.ai/api/v1",
    "xai":          "https://api.x.ai/v1",
    "fireworks":    "https://api.fireworks.ai/inference/v1",
    "nvidia_nim":   "https://integrate.api.nvidia.com/v1",
    # 地端 self-host：沒填 base_url 直接報錯
    "llama_cpp": "", "vllm": "", "sglang": "", "tgi": "", "lmstudio": "",
    "xinference": "", "localai": "", "text_gen_webui": "", "gpt4all": "",
}


async def _sync_openai_compat_models(
    session: AsyncSession, provider_id: str, base_url: str | None, api_key: str | None
) -> None:
    """打 OpenAI 相容 /v1/models，把伺服器上實際存在的模型同步進 ai_models。

    對齊 `_sync_ollama_models` 的「多補少刪」語意（只反映自架伺服器現況）。
    伺服器不可達 / 回非 200 時靜默 return，不動 DB（沿用既有清單）。
    """
    from sqlalchemy import text
    url = (base_url or "").rstrip("/")
    # base_url 可能帶 /v1（OpenAI 相容慣例）→ 補 /models；否則補 /v1/models
    url = url + "/models" if url.endswith("/v1") else url + "/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0)) as client:
            resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            return
        payload = resp.json()
    except Exception as exc:  # noqa: BLE001 — 伺服器沒開不致命
        import structlog
        structlog.get_logger().info("openai_models_sync_skipped", error=str(exc), url=url)
        return

    live: dict[str, str] = {}  # model_name -> model_type（沿用 ollama 的關鍵字推測）
    for m in payload.get("data", []) or []:
        name = m.get("id") or m.get("name") if isinstance(m, dict) else None
        if not name:
            continue
        live[name] = _guess_ollama_model_type(name)
    if not live:
        return

    for name, mtype in live.items():
        await session.execute(text("""
            INSERT INTO ai_models (provider_id, model_name, model_type, display_name, status, is_default, config)
            VALUES (CAST(:pid AS uuid), CAST(:n AS varchar), CAST(:t AS varchar), CAST(:d AS varchar), 'active', FALSE, '{}'::jsonb)
            ON CONFLICT (provider_id, model_name) DO NOTHING
        """), {"pid": provider_id, "n": name, "t": mtype, "d": name})

    await session.execute(text("""
        DELETE FROM ai_models
        WHERE provider_id = CAST(:pid AS uuid)
          AND model_name <> ALL(:keep)
    """), {"pid": provider_id, "keep": list(live.keys())})
    await session.commit()


# 非 openai_compat 但有可 live-fetch 的 list endpoint（各自 auth header 不同）。
# vertex_ai/bedrock（需雲端 SDK/OAuth）+ voyage/jina（無公開 list endpoint）不在此 → 僅靠種子清單。
_SPECIAL_LIST_FETCH = {"gemini", "azure_openai", "deepgram", "elevenlabs", "stability_ai"}


async def _sync_special_provider_models(
    session: AsyncSession, provider_id: str, provider_type: str,
    base_url: str | None, api_key: str | None,
) -> None:
    """非 openai_compat provider 的 best-effort live-fetch（v5.12 scope B）。

    **ADD-only**（不刪既有 seeded — 這些 API 的 list 可能不全，如 deepgram stt/tts 分開）。
    無 api_key / 非 200 / 例外 → 靜默 return，沿用建立時種的預設清單（保證不空）。
    ⚠ 各家 endpoint/auth/回應格式不同；parser 已防禦式處理，抓不到就退種子。
    """
    if not api_key:
        return  # 多數需 key 才能列；沒 key 就靠 seeded 清單
    from sqlalchemy import text
    names: dict[str, str] = {}  # model_name -> model_type
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0)) as client:
            if provider_type == "gemini":
                base = (base_url or "https://generativelanguage.googleapis.com").rstrip("/")
                r = await client.get(f"{base}/v1beta/models", params={"key": api_key})
                if r.status_code != 200:
                    return
                for m in r.json().get("models", []) or []:
                    nm = (m.get("name") or "").split("/")[-1]
                    if nm:
                        names[nm] = "embedding" if "embedding" in nm else "llm"
            elif provider_type == "azure_openai":
                if not base_url:
                    return
                r = await client.get(base_url.rstrip("/") + "/openai/models",
                                     params={"api-version": "2024-10-21"}, headers={"api-key": api_key})
                if r.status_code != 200:
                    return
                for m in r.json().get("data", []) or []:
                    if m.get("id"):
                        names[m["id"]] = _guess_ollama_model_type(m["id"])
            elif provider_type == "deepgram":
                r = await client.get("https://api.deepgram.com/v1/models",
                                     headers={"Authorization": f"Token {api_key}"})
                if r.status_code != 200:
                    return
                p = r.json()
                for grp, mtype in (("stt", "stt"), ("tts", "tts")):
                    for m in p.get(grp, []) or []:
                        nm = m.get("canonical_name") or m.get("name")
                        if nm:
                            names[nm] = mtype
            elif provider_type == "elevenlabs":
                r = await client.get("https://api.elevenlabs.io/v1/models",
                                     headers={"xi-api-key": api_key})
                if r.status_code != 200:
                    return
                data = r.json()
                for m in (data if isinstance(data, list) else data.get("models", [])) or []:
                    nm = m.get("model_id") or m.get("name")
                    if nm:
                        names[nm] = "tts"
            elif provider_type == "stability_ai":
                r = await client.get("https://api.stability.ai/v1/engines/list",
                                     headers={"Authorization": f"Bearer {api_key}"})
                if r.status_code != 200:
                    return
                for m in r.json() or []:
                    if isinstance(m, dict) and m.get("id"):
                        names[m["id"]] = "image"
            else:
                return
    except Exception as exc:  # noqa: BLE001 — 第三方 API 不穩不致命
        import structlog
        structlog.get_logger().info("special_models_sync_skipped", provider_type=provider_type, error=str(exc))
        return

    for nm, mtype in names.items():
        await session.execute(text("""
            INSERT INTO ai_models (provider_id, model_name, model_type, display_name, status, is_default, config)
            VALUES (CAST(:pid AS uuid), CAST(:n AS varchar), CAST(:t AS varchar), CAST(:d AS varchar), 'active', FALSE, '{}'::jsonb)
            ON CONFLICT (provider_id, model_name) DO NOTHING
        """), {"pid": provider_id, "n": nm, "t": mtype, "d": nm})
    if names:
        await session.commit()


def _require_admin(request: Request | None) -> None:
    """檢查請求者是否擁有 admin 角色（從 Gateway 注入的標頭）。"""
    if request is None:
        return
    roles: list[str] = getattr(request.state, "roles", [])
    if "admin" not in roles and "superuser" not in roles:
        raise HTTPException(status_code=403, detail="需要管理員權限")


async def _verify_connection(
    provider_type: str,
    base_url: str | None,
    api_key: str | None,
) -> tuple[bool, str]:
    """向供應商發送測試請求，確認連線是否正常。"""
    timeout = httpx.Timeout(10.0)
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # v5.0.15 / v5.12: openai_compat provider 走 /v1/models verify。預設 base_url 用
    # 模組級 _OPENAI_COMPAT_DEFAULT_BASE（與 list_provider_models 的動態同步共用同一份）。
    # 只有 anthropic / azure / bedrock / gemini 等非 openai_compat 才走專屬驗證流程。
    try:
        if provider_type == "ollama":
            url = (base_url or "http://localhost:11434").rstrip("/") + "/api/tags"
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url)
            if resp.status_code == 200:
                return True, f"Ollama 連線正常（{url}）"
            return False, f"HTTP {resp.status_code}"

        elif provider_type in _OPENAI_COMPAT_DEFAULT_BASE:
            default_base = _OPENAI_COMPAT_DEFAULT_BASE[provider_type]
            effective_base = base_url or default_base
            if not effective_base:
                return False, f"{provider_type} 供應商需提供 base_url"
            url = effective_base.rstrip("/") + "/models"
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return True, f"OpenAI 相容端點連線正常（{provider_type}）"
            return False, f"HTTP {resp.status_code}: {resp.text[:200]}"

        elif provider_type == "anthropic":
            url = (base_url or "https://api.anthropic.com").rstrip("/") + "/v1/models"
            anthropic_headers = {
                "x-api-key": api_key or "",
                "anthropic-version": "2023-06-01",
            }
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, headers=anthropic_headers)
            if resp.status_code == 200:
                return True, "Anthropic 連線正常"
            return False, f"HTTP {resp.status_code}: {resp.text[:200]}"

        elif provider_type == "azure":
            # Azure OpenAI: base_url 應為 https://<resource>.openai.azure.com/
            if not base_url:
                return False, "Azure 供應商需提供 base_url"
            url = base_url.rstrip("/") + "/openai/models?api-version=2024-02-01"
            azure_headers = {"api-key": api_key or ""}
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, headers=azure_headers)
            if resp.status_code == 200:
                return True, "Azure OpenAI 連線正常"
            return False, f"HTTP {resp.status_code}: {resp.text[:200]}"

        else:
            return False, f"不支援的供應商類型：{provider_type}"

    except httpx.ConnectError as exc:
        return False, f"無法連線：{exc}"
    except httpx.TimeoutException:
        return False, "連線逾時"
    except Exception as exc:
        return False, str(exc)
