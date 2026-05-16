"""MiniMax adapter（M3 收尾）。

走 MiniMax ChatCompletion v2 REST：
  POST /v1/text/chatcompletion_v2  （Authorization: Bearer ${api_key}）

訊息格式幾乎與 OpenAI 一致；但部分版本需要把 system 拆到 system_prompt 欄位。
本 adapter 採「直接傳 messages」最大相容路徑；MiniMax 接受 OpenAI 風格 messages。
"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from .base import BaseProvider, ChatRequest, ChatResponse


class MiniMaxProvider(BaseProvider):
    provider_type = "minimax"

    DEFAULT_BASE = "https://api.minimax.chat"

    def __init__(self, api_key: str | None, base_url: str | None = None, config: dict[str, Any] | None = None) -> None:
        super().__init__(api_key, base_url or self.DEFAULT_BASE, config)
        self._client = httpx.AsyncClient(timeout=60.0)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key or ''}",
            "Content-Type":  "application/json",
        }

    def _build_body(self, req: ChatRequest, *, stream: bool) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model":    req.model,
            "messages": req.messages,
            "stream":   stream,
        }
        if req.temperature is not None:
            body["temperature"] = req.temperature
        if req.max_tokens is not None:
            body["max_tokens"] = req.max_tokens
        body.update(req.extra or {})
        return body

    async def chat(self, req: ChatRequest) -> ChatResponse:
        body = self._build_body(req, stream=False)
        r = await self._client.post(
            f"{self.base_url}/v1/text/chatcompletion_v2",
            json=body, headers=self._headers(),
        )
        r.raise_for_status()
        data = r.json()
        choices = data.get("choices") or []
        text = ""
        if choices:
            msg = choices[0].get("message") or {}
            text = msg.get("content") or ""
        usage = data.get("usage") or {}
        return ChatResponse(
            text=text,
            prompt_tokens=int(usage.get("prompt_tokens", 0) or 0),
            completion_tokens=int(usage.get("completion_tokens", 0) or 0),
            total_tokens=int(usage.get("total_tokens", 0) or 0),
            raw=data,
        )

    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[str]:
        body = self._build_body(req, stream=True)
        async with self._client.stream(
            "POST", f"{self.base_url}/v1/text/chatcompletion_v2",
            json=body, headers=self._headers(),
        ) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if not payload or payload == "[DONE]":
                    continue
                try:
                    chunk = json.loads(payload)
                except Exception:
                    continue
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = (choices[0].get("delta") or {}).get("content")
                if delta:
                    yield delta

    async def health(self) -> bool:
        return bool(self.api_key)
