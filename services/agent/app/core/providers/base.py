"""Provider 抽象基底（M3 啟動）。

所有 model provider adapter（OpenAI / Anthropic / Bedrock / Gemini …）
都實作這個介面。Workflow / Application Agent 透過 BaseProvider 呼叫，
不再直接 import AsyncOpenAI。

設計原則：
- async-first
- 串流以 async iterator 表達
- token 計帳由 caller 在收到 ChatResponse 後處理（避免 adapter 自己呼叫 metrics）
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator


@dataclass
class ChatRequest:
    model:       str
    messages:    list[dict[str, Any]]
    temperature: float | None = None
    max_tokens:  int | None   = None
    stream:      bool         = False
    extra:       dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatResponse:
    text:           str
    prompt_tokens:  int = 0
    completion_tokens: int = 0
    total_tokens:   int = 0
    raw:            dict[str, Any] | None = None


@dataclass
class EmbedRequest:
    model:  str
    inputs: list[str]


@dataclass
class EmbedResponse:
    vectors:       list[list[float]]
    prompt_tokens: int = 0
    total_tokens:  int = 0


class BaseProvider(ABC):
    """Provider adapter 抽象基底。

    具體 adapter 在 __init__ 接收：
      - api_key:  str | None
      - base_url: str | None
      - config:   dict[str, Any]  （provider 層級設定）
    """

    provider_type: str = ""

    def __init__(
        self,
        api_key:  str | None,
        base_url: str | None = None,
        config:   dict[str, Any] | None = None,
    ) -> None:
        self.api_key  = api_key
        self.base_url = base_url
        self.config   = config or {}

    # ── chat ────────────────────────────────────────────────────────────
    @abstractmethod
    async def chat(self, req: ChatRequest) -> ChatResponse:
        """Non-streaming chat completion."""

    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[str]:
        """Streaming chat completion. Default fallback: 包裝 non-streaming 一次吐出。

        子類別應 override 為真正的 SSE / iterator。
        """
        resp = await self.chat(req)
        yield resp.text

    # ── embed（可選） ────────────────────────────────────────────────────
    async def embed(self, req: EmbedRequest) -> EmbedResponse:
        raise NotImplementedError(f"{self.provider_type} 尚未實作 embed")

    # ── 連線測試（可選） ────────────────────────────────────────────────
    async def health(self) -> bool:
        """簡單 ping。預設回 True；子類可實作真正的 HEAD/list-models 檢查。"""
        return True
