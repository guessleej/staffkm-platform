"""Cohere adapter（M3 中段-B）。

走 Cohere v2 chat REST：
  POST /v2/chat   （Bearer token；stream=true 走 SSE）

訊息格式：與 OpenAI 幾乎相同（role: system/user/assistant），直接傳。
"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from .base import BaseProvider, ChatRequest, ChatResponse


class CohereProvider(BaseProvider):
    provider_type = "cohere"

    DEFAULT_BASE = "https://api.cohere.com"

    def __init__(self, api_key: str | None, base_url: str | None = None, config: dict[str, Any] | None = None) -> None:
        super().__init__(api_key, base_url or self.DEFAULT_BASE, config)
        self._client = httpx.AsyncClient(timeout=60.0)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key or ''}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
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
        r = await self._client.post(f"{self.base_url}/v2/chat", json=body, headers=self._headers())
        r.raise_for_status()
        data = r.json()
        msg = (data.get("message") or {})
        parts = msg.get("content") or []
        text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
        usage = (data.get("usage") or {}).get("tokens") or {}
        in_tk  = int(usage.get("input_tokens") or 0)
        out_tk = int(usage.get("output_tokens") or 0)
        return ChatResponse(
            text=text,
            prompt_tokens=in_tk,
            completion_tokens=out_tk,
            total_tokens=in_tk + out_tk,
            raw=data,
        )

    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[str]:
        body = self._build_body(req, stream=True)
        async with self._client.stream(
            "POST", f"{self.base_url}/v2/chat", json=body, headers=self._headers(),
        ) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line:
                    continue
                # Cohere v2 SSE: 直接 JSON-per-line（也接受 "data: " prefix）
                payload = line[5:].strip() if line.startswith("data:") else line.strip()
                if not payload or payload == "[DONE]":
                    continue
                try:
                    ev = json.loads(payload)
                except Exception:
                    continue
                if ev.get("type") == "content-delta":
                    delta = ((ev.get("delta") or {}).get("message") or {}).get("content") or {}
                    t = delta.get("text") if isinstance(delta, dict) else None
                    if t:
                        yield t

    async def health(self) -> bool:
        if not self.api_key:
            return False
        try:
            r = await self._client.get(
                f"{self.base_url}/v1/models", headers=self._headers(),
            )
            return r.status_code == 200
        except Exception:
            return False
