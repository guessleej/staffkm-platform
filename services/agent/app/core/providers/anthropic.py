"""Anthropic Claude adapter（M3 中段）。

Anthropic 的 Messages API 與 OpenAI 不同：
- system prompt 是頂層欄位，不在 messages 內
- messages 只接受 user / assistant 兩種 role
- 串流走 client.messages.stream(...)

本 adapter 自動把 OpenAI 格式（含 system 訊息）轉成 Anthropic 格式。
"""
from __future__ import annotations

from typing import Any, AsyncIterator

from anthropic import AsyncAnthropic

from .base import BaseProvider, ChatRequest, ChatResponse


def _split_system(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """把 OpenAI 風格 messages 拆成 (system_prompt, user/assistant_messages)。

    多個 system 會被串接成單一字串。non-user/assistant 的 role 會被丟棄。
    """
    sys_parts: list[str] = []
    out: list[dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        content = m.get("content", "")
        if role == "system":
            if content:
                sys_parts.append(content if isinstance(content, str) else str(content))
        elif role in ("user", "assistant"):
            out.append({"role": role, "content": content})
    return "\n\n".join(sys_parts), out


class AnthropicProvider(BaseProvider):
    provider_type = "anthropic"

    def __init__(self, api_key: str | None, base_url: str | None = None, config: dict[str, Any] | None = None) -> None:
        super().__init__(api_key, base_url, config)
        kwargs: dict[str, Any] = {"api_key": api_key or ""}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = AsyncAnthropic(**kwargs)

    async def chat(self, req: ChatRequest) -> ChatResponse:
        sys_prompt, msgs = _split_system(req.messages)
        kwargs: dict[str, Any] = {
            "model":      req.model,
            "messages":   msgs,
            "max_tokens": req.max_tokens or 2048,
        }
        if sys_prompt:
            kwargs["system"] = sys_prompt
        if req.temperature is not None:
            kwargs["temperature"] = req.temperature
        kwargs.update(req.extra or {})

        resp = await self._client.messages.create(**kwargs)
        # resp.content 是 ContentBlock list；取所有 text 段落
        text_parts: list[str] = []
        for block in (resp.content or []):
            t = getattr(block, "text", None)
            if t:
                text_parts.append(t)
        text = "".join(text_parts)
        usage = getattr(resp, "usage", None)
        return ChatResponse(
            text=text,
            prompt_tokens=getattr(usage, "input_tokens", 0) or 0,
            completion_tokens=getattr(usage, "output_tokens", 0) or 0,
            total_tokens=(
                (getattr(usage, "input_tokens", 0) or 0)
                + (getattr(usage, "output_tokens", 0) or 0)
            ),
            raw=resp.model_dump() if hasattr(resp, "model_dump") else None,
        )

    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[str]:
        sys_prompt, msgs = _split_system(req.messages)
        kwargs: dict[str, Any] = {
            "model":      req.model,
            "messages":   msgs,
            "max_tokens": req.max_tokens or 2048,
        }
        if sys_prompt:
            kwargs["system"] = sys_prompt
        if req.temperature is not None:
            kwargs["temperature"] = req.temperature
        kwargs.update(req.extra or {})

        async with self._client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                if text:
                    yield text

    async def health(self) -> bool:
        # Anthropic 無 list_models endpoint；做個最小 messages 探測太貴。
        # 這裡只檢查 client 是否能建立，回 True；真實連線錯誤在 chat() 時才會浮現。
        return self._client is not None
