"""MCP HTTP/SSE client（M4 啟動 — minimal）。

對標 Model Context Protocol：
- transport=http：POST 一個 JSON-RPC message
- transport=sse：SSE bidirectional
- transport=stdio：subprocess（M4 中段補）

此處只實作 v1：列出 tools / 呼叫 tool（http transport）。
正式 MCP 走 jsonrpc id/method/params；伺服端 method:
  - tools/list
  - tools/call
"""
from __future__ import annotations

import uuid
from typing import Any

import httpx


class MCPClient:
    def __init__(self, url: str, *, headers: dict[str, str] | None = None, timeout: float = 30.0):
        self.url = url.rstrip("/")
        self._headers = headers or {}
        self._client = httpx.AsyncClient(timeout=timeout)

    async def _rpc(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        body = {
            "jsonrpc": "2.0",
            "id":      str(uuid.uuid4()),
            "method":  method,
            "params":  params or {},
        }
        r = await self._client.post(self.url, json=body, headers=self._headers)
        r.raise_for_status()
        data = r.json()
        if "error" in data and data["error"]:
            raise RuntimeError(f"MCP error: {data['error']}")
        return data.get("result") or {}

    async def list_tools(self) -> list[dict[str, Any]]:
        res = await self._rpc("tools/list")
        return res.get("tools") or []

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self._rpc("tools/call", {"name": name, "arguments": arguments})

    async def aclose(self) -> None:
        await self._client.aclose()
