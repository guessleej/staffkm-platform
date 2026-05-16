"""Google Gemini adapter（M3 中段-B）。

走 generativelanguage REST：
  POST /v1beta/models/{model}:streamGenerateContent?key={API_KEY}

訊息格式轉換：
- OpenAI 風格 messages → Gemini contents（role: user/model + parts:[{text:...}]）
- system 訊息合併進 systemInstruction
"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from .base import BaseProvider, ChatRequest, ChatResponse


def _to_gemini(messages: list[dict[str, Any]]) -> tuple[dict | None, list[dict]]:
    sys_parts: list[str] = []
    contents: list[dict] = []
    for m in messages:
        role = m.get("role")
        content = m.get("content", "")
        if not isinstance(content, str):
            content = str(content)
        if role == "system":
            if content:
                sys_parts.append(content)
        elif role == "user":
            contents.append({"role": "user", "parts": [{"text": content}]})
        elif role == "assistant":
            contents.append({"role": "model", "parts": [{"text": content}]})
    system_instruction = None
    if sys_parts:
        system_instruction = {"parts": [{"text": "\n\n".join(sys_parts)}]}
    return system_instruction, contents


class GeminiProvider(BaseProvider):
    provider_type = "gemini"

    DEFAULT_BASE = "https://generativelanguage.googleapis.com"

    def __init__(self, api_key: str | None, base_url: str | None = None, config: dict[str, Any] | None = None) -> None:
        super().__init__(api_key, base_url or self.DEFAULT_BASE, config)
        self._client = httpx.AsyncClient(timeout=60.0)

    def _build_body(self, req: ChatRequest) -> dict[str, Any]:
        sys_inst, contents = _to_gemini(req.messages)
        body: dict[str, Any] = {"contents": contents}
        if sys_inst:
            body["systemInstruction"] = sys_inst
        gen_config: dict[str, Any] = {}
        if req.temperature is not None:
            gen_config["temperature"] = req.temperature
        if req.max_tokens is not None:
            gen_config["maxOutputTokens"] = req.max_tokens
        if gen_config:
            body["generationConfig"] = gen_config
        return body

    def _url(self, model: str, streaming: bool) -> str:
        verb = "streamGenerateContent" if streaming else "generateContent"
        url = f"{self.base_url}/v1beta/models/{model}:{verb}"
        if streaming:
            url += "?alt=sse"
        if self.api_key:
            url += ("&" if "?" in url else "?") + f"key={self.api_key}"
        return url

    async def chat(self, req: ChatRequest) -> ChatResponse:
        body = self._build_body(req)
        r = await self._client.post(self._url(req.model, streaming=False), json=body)
        r.raise_for_status()
        data = r.json()
        cands = data.get("candidates") or []
        text = ""
        if cands:
            parts = (cands[0].get("content") or {}).get("parts") or []
            text = "".join(p.get("text", "") for p in parts)
        usage = data.get("usageMetadata") or {}
        return ChatResponse(
            text=text,
            prompt_tokens=usage.get("promptTokenCount", 0) or 0,
            completion_tokens=usage.get("candidatesTokenCount", 0) or 0,
            total_tokens=usage.get("totalTokenCount", 0) or 0,
            raw=data,
        )

    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[str]:
        body = self._build_body(req)
        async with self._client.stream("POST", self._url(req.model, streaming=True), json=body) as r:
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
                cands = chunk.get("candidates") or []
                if not cands:
                    continue
                parts = (cands[0].get("content") or {}).get("parts") or []
                for p in parts:
                    t = p.get("text")
                    if t:
                        yield t

    async def health(self) -> bool:
        if not self.api_key:
            return False
        try:
            r = await self._client.get(f"{self.base_url}/v1beta/models?key={self.api_key}")
            return r.status_code == 200
        except Exception:
            return False
