"""Google Vertex AI adapter（M3 收尾）。

Vertex AI 的 Gemini 模型走：
  POST {region}-aiplatform.googleapis.com/v1/projects/{project}/locations/{region}/publishers/google/models/{model}:streamGenerateContent

訊息格式與 Gemini 完全一致（contents + systemInstruction + generationConfig）。
與 GeminiProvider 不同處：
- 認證走 OAuth bearer token（service account），不能用 API key
- base_url 內含 region；project_id 走 config 欄位

本 adapter 預期 config 帶：
  - region:      ex. us-central1
  - project_id:  GCP project id
  - access_token: 由 ops 預先用 service account 取得（短期 token；長期可換 google-auth）

若沒裝 google-auth，採「ops 提供現成 access_token」最簡路徑；
M3 收尾後可考慮加 google-auth 依賴自動 refresh。
"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from .base import BaseProvider, ChatRequest, ChatResponse
from .gemini import _to_gemini


class VertexAIProvider(BaseProvider):
    provider_type = "vertex_ai"

    def __init__(self, api_key: str | None, base_url: str | None = None, config: dict[str, Any] | None = None) -> None:
        super().__init__(api_key, base_url, config)
        self._client = httpx.AsyncClient(timeout=60.0)
        self._region     = self.config.get("region") or "us-central1"
        self._project_id = self.config.get("project_id") or ""
        # 三選一：明示 access_token > api_key > 空字串（後者由 health() 報告）
        self._access_token = self.config.get("access_token") or api_key or ""

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type":  "application/json",
        }

    def _url(self, model: str, streaming: bool) -> str:
        verb = "streamGenerateContent" if streaming else "generateContent"
        base = (
            self.base_url
            or f"https://{self._region}-aiplatform.googleapis.com"
        )
        url = (
            f"{base}/v1/projects/{self._project_id}/locations/{self._region}"
            f"/publishers/google/models/{model}:{verb}"
        )
        if streaming:
            url += "?alt=sse"
        return url

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

    async def chat(self, req: ChatRequest) -> ChatResponse:
        body = self._build_body(req)
        r = await self._client.post(self._url(req.model, streaming=False), json=body, headers=self._headers())
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
        async with self._client.stream(
            "POST", self._url(req.model, streaming=True),
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
                cands = chunk.get("candidates") or []
                if not cands:
                    continue
                parts = (cands[0].get("content") or {}).get("parts") or []
                for p in parts:
                    t = p.get("text")
                    if t:
                        yield t

    async def health(self) -> bool:
        return bool(self._access_token and self._project_id)
