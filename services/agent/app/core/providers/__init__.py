"""Model Provider 抽象介面（M3 啟動）。

公開三個東西：
- BaseProvider：所有 provider adapter 的抽象基底
- PROVIDER_REGISTRY：20+ provider 的中繼資料（type / 顯示名稱 / 預設 base_url / 預設 model 等）
- get_adapter(provider_type)：依 type 取得 adapter class

註：M3 啟動階段只先提供 OpenAI-compatible adapter；
其餘 provider 走相同介面，後續 PR 補上專屬 adapter（如 Anthropic / Bedrock / Gemini 等）。
"""
from .anthropic import AnthropicProvider
from .base import BaseProvider, ChatRequest, ChatResponse, EmbedRequest, EmbedResponse
from .openai_compat import OpenAICompatProvider
from .registry import PROVIDER_REGISTRY, ProviderMeta, get_adapter, list_providers

__all__ = [
    "AnthropicProvider",
    "BaseProvider",
    "ChatRequest",
    "ChatResponse",
    "EmbedRequest",
    "EmbedResponse",
    "OpenAICompatProvider",
    "PROVIDER_REGISTRY",
    "ProviderMeta",
    "get_adapter",
    "list_providers",
]
