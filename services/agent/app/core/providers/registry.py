"""Provider Registry — 20+ provider 的中繼資料（M3 啟動）。

每筆紀錄包含：
- type            字串 ID（DB model_providers.provider_type 對應）
- label           顯示名稱
- adapter_type    走哪個 adapter（目前先全部走 openai_compat；
                   anthropic/bedrock/gemini/cohere/vertex 待後續 PR 補專屬 adapter）
- default_base_url
- recommended_models  常見可用 model id 清單（前端建議用）
- needs_api_key   是否強制要 api key（地端 ollama / vllm 可選）
- notes           中文備註

M3 啟動只先「列得出 20+ provider」+「OpenAI-compatible 都能跑」，
專屬 adapter 由 M3 中段 PR 補。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Type

from .anthropic import AnthropicProvider
from .base import BaseProvider
from .bedrock import BedrockProvider
from .cohere import CohereProvider
from .gemini import GeminiProvider
from .openai_compat import OpenAICompatProvider


@dataclass
class ProviderMeta:
    type:                str
    label:               str
    adapter_type:        str
    default_base_url:    str | None = None
    recommended_models:  list[str]  = field(default_factory=list)
    needs_api_key:       bool       = True
    notes:               str        = ""


# ── 20+ providers ──────────────────────────────────────────────────────
PROVIDER_REGISTRY: list[ProviderMeta] = [
    # ── 1) 地端優先（staffKM 預設） ──────────────────────────────────────
    ProviderMeta("ollama", "Ollama（地端）", "openai_compat",
                 default_base_url="http://ollama:11434/v1",
                 recommended_models=["gemma4:e4b", "qwen2.5:7b", "llama3.1:8b"],
                 needs_api_key=False,
                 notes="staffKM 預設地端 LLM；硬鎖 gemma4:e4b。"),
    ProviderMeta("vllm", "vLLM（地端）", "openai_compat",
                 default_base_url="http://vllm:8000/v1",
                 recommended_models=["Qwen/Qwen2.5-7B-Instruct"],
                 needs_api_key=False),
    ProviderMeta("xinference", "Xinference（地端）", "openai_compat",
                 default_base_url="http://xinference:9997/v1",
                 needs_api_key=False),
    ProviderMeta("localai", "LocalAI（地端）", "openai_compat",
                 default_base_url="http://localai:8080/v1",
                 needs_api_key=False),

    # ── 2) 國際雲端 ─────────────────────────────────────────────────────
    ProviderMeta("openai", "OpenAI", "openai_compat",
                 default_base_url="https://api.openai.com/v1",
                 recommended_models=["gpt-4o-mini", "gpt-4o", "o4-mini"]),
    ProviderMeta("azure_openai", "Azure OpenAI", "openai_compat",
                 notes="base_url 形如 https://{resource}.openai.azure.com/openai/deployments/{deployment}"),
    ProviderMeta("anthropic", "Anthropic Claude", "anthropic",
                 default_base_url="https://api.anthropic.com",
                 recommended_models=["claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-4-5"],
                 notes="走 messages API；system 自動拆成頂層欄位。"),
    ProviderMeta("bedrock", "AWS Bedrock", "bedrock",
                 notes="走 aioboto3 + SigV4；目前支援 Claude on Bedrock。需在部署環境安裝 aioboto3。"),
    ProviderMeta("gemini", "Google Gemini", "gemini",
                 default_base_url="https://generativelanguage.googleapis.com",
                 recommended_models=["gemini-2.5-pro", "gemini-2.5-flash"],
                 notes="走 generateContent REST + API key；system 自動轉 systemInstruction。"),
    ProviderMeta("vertex_ai", "Google Vertex AI", "vertex_ai",
                 notes="需 GCP service account；後續 PR 接入。"),
    ProviderMeta("cohere", "Cohere", "cohere",
                 default_base_url="https://api.cohere.com",
                 recommended_models=["command-r-plus", "command-r"],
                 notes="走 Cohere v2 chat REST + Bearer token。"),
    ProviderMeta("mistral", "Mistral AI", "openai_compat",
                 default_base_url="https://api.mistral.ai/v1",
                 recommended_models=["mistral-large-latest", "mistral-small-latest"]),
    ProviderMeta("groq", "Groq", "openai_compat",
                 default_base_url="https://api.groq.com/openai/v1"),
    ProviderMeta("together", "Together AI", "openai_compat",
                 default_base_url="https://api.together.xyz/v1"),
    ProviderMeta("perplexity", "Perplexity", "openai_compat",
                 default_base_url="https://api.perplexity.ai"),
    ProviderMeta("openrouter", "OpenRouter", "openai_compat",
                 default_base_url="https://openrouter.ai/api/v1",
                 notes="統一接 200+ 模型的路由服務。"),

    # ── 3) 中文 / 亞洲雲端 ──────────────────────────────────────────────
    ProviderMeta("deepseek", "DeepSeek", "openai_compat",
                 default_base_url="https://api.deepseek.com/v1",
                 recommended_models=["deepseek-chat", "deepseek-reasoner"]),
    ProviderMeta("zhipu", "智譜 GLM", "openai_compat",
                 default_base_url="https://open.bigmodel.cn/api/paas/v4",
                 recommended_models=["glm-4-plus", "glm-4-air"]),
    ProviderMeta("moonshot", "Moonshot (Kimi)", "openai_compat",
                 default_base_url="https://api.moonshot.cn/v1",
                 recommended_models=["moonshot-v1-8k", "moonshot-v1-32k"]),
    ProviderMeta("qwen", "通義千問 (DashScope)", "openai_compat",
                 default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                 recommended_models=["qwen-max", "qwen-plus"]),
    ProviderMeta("baichuan", "百川 (Baichuan)", "openai_compat",
                 default_base_url="https://api.baichuan-ai.com/v1"),
    ProviderMeta("minimax", "MiniMax", "minimax",
                 default_base_url="https://api.minimax.chat",
                 notes="後續 PR 接入專屬 adapter。"),
    ProviderMeta("siliconflow", "SiliconFlow", "openai_compat",
                 default_base_url="https://api.siliconflow.cn/v1"),
    ProviderMeta("yi", "01.AI (Yi)", "openai_compat",
                 default_base_url="https://api.lingyiwanwu.com/v1"),
    ProviderMeta("doubao", "字節豆包 (Doubao)", "openai_compat",
                 default_base_url="https://ark.cn-beijing.volces.com/api/v3"),
]


# adapter_type → class 對應
_ADAPTER_TABLE: dict[str, Type[BaseProvider]] = {
    "openai_compat": OpenAICompatProvider,
    "anthropic":  AnthropicProvider,   # M3 中段-A
    "gemini":     GeminiProvider,      # M3 中段-B
    "cohere":     CohereProvider,      # M3 中段-B
    "bedrock":    BedrockProvider,     # M3 中段-B（需 aioboto3）
    # 以下尚未實作，fallback 到 OpenAICompatProvider 以避免執行期錯誤
    "vertex_ai":  OpenAICompatProvider,
    "minimax":    OpenAICompatProvider,
}


def get_adapter(provider_type: str) -> Type[BaseProvider]:
    """依 type 取得 adapter class（找不到時 fallback 到 OpenAICompatProvider）。"""
    # provider_type 可能是 registry 內的 type；先查 registry 拿到 adapter_type
    for meta in PROVIDER_REGISTRY:
        if meta.type == provider_type:
            return _ADAPTER_TABLE.get(meta.adapter_type, OpenAICompatProvider)
    # 不在 registry → 退回 openai_compat
    return OpenAICompatProvider


def list_providers() -> list[dict]:
    """給 API/前端用，回傳 JSON-friendly dict 清單。"""
    return [
        {
            "type":               m.type,
            "label":              m.label,
            "adapter_type":       m.adapter_type,
            "default_base_url":   m.default_base_url,
            "recommended_models": m.recommended_models,
            "needs_api_key":      m.needs_api_key,
            "notes":              m.notes,
        }
        for m in PROVIDER_REGISTRY
    ]
