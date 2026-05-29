"""模型抓取覆蓋守衛（賣錢系統：每個 openai_compat provider 都要能動態抓模型）。

v5.12 scope A：模型清單動態同步（/v1/models）從「只有 5 個自架 type」擴大到**所有
openai_compat type**。本檔把「哪些 type 走動態抓」鎖住，避免日後新增 provider 漏接
→ admin 加了看到空清單（賣錢系統大忌）。

純斷言、不需 DB（但 import app.api.models 連帶 fastapi/sqlalchemy → 放整合層跑）。
"""
from __future__ import annotations

from app.api.models import (
    _DEFAULT_MODELS_ON_CREATE,
    _OPENAI_COMPAT_DEFAULT_BASE,
    _SPECIAL_LIST_FETCH,
)


# registry 全部 31 個 provider type（鏡像 services/agent/.../providers/registry.py；
# registry 新增 type 時這份要同步更新，否則本守衛會紅 → 提醒「新 provider 沒接抓模型」）。
_ALL_REGISTRY_TYPES = {
    "openai", "anthropic", "gemini", "vertex_ai", "bedrock", "azure_openai",
    "cohere", "mistral", "groq", "together", "fireworks", "perplexity",
    "openrouter", "xai", "nvidia_nim", "moonshot", "deepgram", "elevenlabs",
    "stability_ai", "jina", "voyage", "ollama", "llama_cpp", "vllm", "sglang",
    "tgi", "lmstudio", "localai", "text_gen_webui", "gpt4all", "xinference",
}


# scope A 必須涵蓋的 openai 相容 provider（雲端 + 自架）→ 都要走 /v1/models 動態抓
_MUST_DYNAMIC = {
    # 自架（原本就有）
    "llama_cpp", "vllm", "sglang", "tgi", "lmstudio",
    "xinference", "localai", "text_gen_webui", "gpt4all",
    # 雲端 openai 相容（scope A 新納入）
    "openai", "moonshot", "groq", "together", "mistral",
    "perplexity", "openrouter", "xai", "fireworks", "nvidia_nim",
}


def test_all_openai_compat_providers_are_dynamic_fetchable():
    """每個 openai 相容 provider 都在 /v1/models 動態同步 gate 裡（賣錢系統保證）。"""
    missing = _MUST_DYNAMIC - set(_OPENAI_COMPAT_DEFAULT_BASE.keys())
    assert not missing, f"以下 openai_compat provider 沒接動態抓模型（會空清單）: {sorted(missing)}"


def test_self_hosted_have_empty_default_base():
    """自架 type 預設 base 為空字串（強制 user 自填 base_url；沒填不該亂打雲端）。"""
    for t in ("llama_cpp", "vllm", "sglang", "tgi", "lmstudio",
              "xinference", "localai", "text_gen_webui", "gpt4all"):
        assert _OPENAI_COMPAT_DEFAULT_BASE.get(t) == "", f"{t} 不該有預設雲端 base"


def test_cloud_providers_have_default_base():
    """雲端 openai 相容 type 有預設 base_url（user 沒填也能抓）。"""
    for t in ("openai", "together", "fireworks", "perplexity", "nvidia_nim", "groq", "mistral"):
        base = _OPENAI_COMPAT_DEFAULT_BASE.get(t)
        assert base and base.startswith("http"), f"{t} 缺預設 base_url"


def test_every_registry_provider_has_model_source():
    """scope B 核心保證「31 個全包」：每個 registry provider 加了都有模型來源
    （動態 ollama / 動態 openai_compat / live-fetch special / 種子預設）→ 永不空清單。"""
    covered = (
        {"ollama"}                              # /api/tags 動態
        | set(_OPENAI_COMPAT_DEFAULT_BASE)      # /v1/models 動態
        | set(_SPECIAL_LIST_FETCH)              # 特殊 API live-fetch
        | set(_DEFAULT_MODELS_ON_CREATE)        # 種子預設
    )
    missing = _ALL_REGISTRY_TYPES - covered
    assert not missing, f"以下 provider 加了會空清單（沒接任何模型來源）: {sorted(missing)}"


def test_special_fetch_providers_also_seeded():
    """live-fetch 的 special provider 都有種子 fallback（無 key/抓失敗也不空）。"""
    for t in _SPECIAL_LIST_FETCH:
        assert t in _DEFAULT_MODELS_ON_CREATE, f"{t} 有 live-fetch 但無種子 fallback"
