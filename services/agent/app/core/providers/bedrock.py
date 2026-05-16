"""AWS Bedrock adapter（M3 中段-B）。

Bedrock 走 AWS SigV4 簽章；最乾淨的接法是 boto3 / aioboto3，但這會引入較重依賴。
本 adapter 採取「optional import」策略：

- 若部署環境裝了 aioboto3：使用 bedrock-runtime invoke_model_with_response_stream
- 否則：raise NotImplementedError，明確提示 ops 要裝 aioboto3 + 設 AWS 認證

訊息格式依目標 model 而異；目前先支援 Anthropic on Bedrock（messages 結構，
與 anthropic SDK 一致，但走 Bedrock invoke）。其他模型留給後續 PR。
"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

from .base import BaseProvider, ChatRequest, ChatResponse


def _split_system(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
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


class BedrockProvider(BaseProvider):
    """AWS Bedrock 上的 Claude（後續可擴充 Titan / Llama / Mistral）。

    config 期望欄位：
      - region:           AWS region（預設 us-east-1）
      - access_key_id:    可選，省略則走 boto 預設 credential chain
      - secret_access_key:可選
      - session_token:    可選
    """
    provider_type = "bedrock"

    def __init__(self, api_key: str | None, base_url: str | None = None, config: dict[str, Any] | None = None) -> None:
        super().__init__(api_key, base_url, config)
        self._region = (self.config.get("region") or "us-east-1")

    def _ensure_aioboto3(self):
        try:
            import aioboto3  # noqa: F401
            return aioboto3
        except ImportError as e:
            raise NotImplementedError(
                "Bedrock adapter 需要安裝 aioboto3 並設定 AWS 認證。"
                "請在 services/agent 加入 aioboto3 依賴，或改用 OpenAI-compatible bedrock gateway。"
            ) from e

    def _session(self):
        aioboto3 = self._ensure_aioboto3()
        kwargs: dict[str, Any] = {"region_name": self._region}
        ak = self.config.get("access_key_id")
        sk = self.config.get("secret_access_key")
        tk = self.config.get("session_token")
        if ak and sk:
            kwargs["aws_access_key_id"] = ak
            kwargs["aws_secret_access_key"] = sk
            if tk:
                kwargs["aws_session_token"] = tk
        return aioboto3.Session(**kwargs)

    def _build_anthropic_body(self, req: ChatRequest) -> dict[str, Any]:
        sys_prompt, msgs = _split_system(req.messages)
        body: dict[str, Any] = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages":          msgs,
            "max_tokens":        req.max_tokens or 2048,
        }
        if sys_prompt:
            body["system"] = sys_prompt
        if req.temperature is not None:
            body["temperature"] = req.temperature
        return body

    async def chat(self, req: ChatRequest) -> ChatResponse:
        session = self._session()
        body = self._build_anthropic_body(req)
        async with session.client("bedrock-runtime") as client:
            resp = await client.invoke_model(
                modelId=req.model,
                body=json.dumps(body).encode(),
                contentType="application/json",
                accept="application/json",
            )
            raw = await resp["body"].read()
            data = json.loads(raw)
        text_parts = [b.get("text", "") for b in (data.get("content") or []) if isinstance(b, dict)]
        usage = data.get("usage") or {}
        return ChatResponse(
            text="".join(text_parts),
            prompt_tokens=usage.get("input_tokens", 0) or 0,
            completion_tokens=usage.get("output_tokens", 0) or 0,
            total_tokens=(usage.get("input_tokens", 0) or 0) + (usage.get("output_tokens", 0) or 0),
            raw=data,
        )

    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[str]:
        session = self._session()
        body = self._build_anthropic_body(req)
        async with session.client("bedrock-runtime") as client:
            resp = await client.invoke_model_with_response_stream(
                modelId=req.model,
                body=json.dumps(body).encode(),
                contentType="application/json",
                accept="application/json",
            )
            async for event in resp["body"]:
                chunk = event.get("chunk")
                if not chunk:
                    continue
                payload = json.loads(chunk["bytes"])
                if payload.get("type") == "content_block_delta":
                    delta = payload.get("delta") or {}
                    t = delta.get("text")
                    if t:
                        yield t

    async def health(self) -> bool:
        try:
            self._ensure_aioboto3()
            return True
        except NotImplementedError:
            return False
