"""OpenAI-compatible adapter（M3 啟動）。

凡是支援 OpenAI Chat Completions / Embeddings 介面的 provider 都可以共用這個 adapter：
- OpenAI、Azure OpenAI（須在 config 帶 deployment）
- Ollama（base_url=http://ollama:11434/v1）
- DeepSeek、Moonshot、Zhipu、Qwen-DashScope、Together、Groq、Mistral、SiliconFlow、Perplexity…

未涵蓋的（Anthropic / Bedrock / Gemini / Cohere / VertexAI）後續以專屬 adapter 接入。
"""
from __future__ import annotations

from typing import Any, AsyncIterator

from openai import AsyncOpenAI

from .base import BaseProvider, ChatRequest, ChatResponse, EmbedRequest, EmbedResponse


class OpenAICompatProvider(BaseProvider):
    provider_type = "openai_compat"

    def __init__(self, api_key: str | None, base_url: str | None = None, config: dict[str, Any] | None = None) -> None:
        super().__init__(api_key, base_url, config)
        client_kwargs: dict[str, Any] = {"api_key": api_key or "sk-not-needed"}
        if base_url:
            client_kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**client_kwargs)

    async def chat(self, req: ChatRequest) -> ChatResponse:
        kwargs: dict[str, Any] = {
            "model":    req.model,
            "messages": req.messages,
            "stream":   False,
        }
        if req.temperature is not None:
            kwargs["temperature"] = req.temperature
        if req.max_tokens is not None:
            kwargs["max_tokens"] = req.max_tokens
        kwargs.update(req.extra or {})

        resp = await self._client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        text = (choice.message.content or "") if choice and choice.message else ""
        usage = getattr(resp, "usage", None)
        return ChatResponse(
            text=text,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            total_tokens=getattr(usage, "total_tokens", 0) or 0,
            raw=resp.model_dump() if hasattr(resp, "model_dump") else None,
        )

    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[str]:
        kwargs: dict[str, Any] = {
            "model":    req.model,
            "messages": req.messages,
            "stream":   True,
        }
        if req.temperature is not None:
            kwargs["temperature"] = req.temperature
        if req.max_tokens is not None:
            kwargs["max_tokens"] = req.max_tokens
        kwargs.update(req.extra or {})

        stream = await self._client.chat.completions.create(**kwargs)
        async for chunk in stream:
            try:
                delta = chunk.choices[0].delta
                token = getattr(delta, "content", None) or ""
                if token:
                    yield token
            except Exception:
                continue

    async def embed(self, req: EmbedRequest) -> EmbedResponse:
        resp = await self._client.embeddings.create(model=req.model, input=req.inputs)
        usage = getattr(resp, "usage", None)
        return EmbedResponse(
            vectors=[d.embedding for d in resp.data],
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            total_tokens=getattr(usage, "total_tokens", 0) or 0,
        )

    async def health(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False
