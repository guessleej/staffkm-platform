"""Tool 執行 endpoint（RFC-006 D-1）。

支援 kind：
  - http：依 config.url / method / headers / body_template 發出 HTTP
  - mcp：依 config.server_url / tool_name 走 JSON-RPC 2.0 tools/call

注意：shell / custom 暫不支援（沙箱安全議題另案處理）。
所有執行以 workspace 範圍隔離；inputs 透過 {{var}} 模板注入 url / body。
"""
import json
import time
import uuid

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_member

log = structlog.get_logger()
router = APIRouter()


class ToolExecRequest(BaseModel):
    inputs: dict = Field(default_factory=dict)


class ToolExecResponse(BaseModel):
    success:   bool
    status:    int | None = None        # HTTP status；MCP 走 jsonrpc 沒有
    output:    dict | None = None
    text:      str | None = None
    elapsed_ms: int
    error:     str | None = None


def _render(template: str, inputs: dict) -> str:
    out = template
    for k, v in inputs.items():
        out = out.replace(f"{{{{{k}}}}}", str(v))
    return out


async def _exec_http(config: dict, inputs: dict) -> ToolExecResponse:
    method  = (config.get("method") or "GET").upper()
    url     = _render(config.get("url") or "", inputs)
    headers = dict(config.get("headers") or {})
    timeout = float(config.get("timeout", 30.0))
    body_template = config.get("body_template") or ""
    body_str = _render(body_template, inputs) if body_template else ""
    try:
        body_json = json.loads(body_str) if body_str.strip() else None
    except json.JSONDecodeError:
        body_json = None
    if not url:
        raise HTTPException(status_code=400, detail="config.url 未設定")

    from staffkm_core.utils.net import UnsafeURLError, safe_request
    started = time.monotonic()
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await safe_request(client, method, url, headers=headers, json=body_json)
        except UnsafeURLError as e:
            raise HTTPException(status_code=400, detail=f"URL 被 SSRF 防護擋下：{e}")
    elapsed = int((time.monotonic() - started) * 1000)
    out_json = None
    try:
        out_json = resp.json()
    except Exception:
        pass
    return ToolExecResponse(
        success=resp.status_code < 400,
        status=resp.status_code,
        output=out_json,
        text=None if out_json else resp.text[:2000],
        elapsed_ms=elapsed,
    )


async def _exec_mcp(config: dict, inputs: dict) -> ToolExecResponse:
    server_url = (config.get("server_url") or "").rstrip("/")
    tool_name  = config.get("tool_name") or ""
    timeout    = float(config.get("timeout", 30.0))
    if not server_url or not tool_name:
        raise HTTPException(status_code=400, detail="config.server_url 與 tool_name 必填")

    payload = {
        "jsonrpc": "2.0", "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": inputs},
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if api_key := config.get("api_key"):
        headers["Authorization"] = f"Bearer {api_key}"

    from staffkm_core.utils.net import UnsafeURLError, assert_safe_url
    mcp_url = f"{server_url}/mcp"
    try:
        await assert_safe_url(mcp_url)
    except UnsafeURLError as e:
        raise HTTPException(status_code=400, detail=f"MCP server URL 被 SSRF 防護擋下：{e}")
    started = time.monotonic()
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(mcp_url, json=payload, headers=headers)
    elapsed = int((time.monotonic() - started) * 1000)
    data = None
    try:
        data = resp.json()
    except Exception:
        pass
    return ToolExecResponse(
        success=resp.status_code < 400 and (data or {}).get("error") is None,
        status=resp.status_code,
        output=data,
        elapsed_ms=elapsed,
    )


async def _exec_code(code: str, inputs: dict) -> ToolExecResponse:
    """執行 custom / AI 生成的 `def run(**kwargs) -> dict` Python 程式碼（v5.10.5）。

    走 sandbox.run_sandboxed（rlimit + wall-clock timeout + 環境清空），
    以 stdin 傳 JSON 參數，從 stdout marker 之後取回 JSON 結果。
    注意：M2 sandbox 尚無網路 / fs namespace 隔離（見 sandbox.py M4 升級路徑）。
    """
    from app.core.sandbox import run_python_code

    if not code or "def run" not in code:
        raise HTTPException(status_code=400, detail="tool.code 缺少 def run(**kwargs)")

    # v5.10.8：harness/sandbox 已抽到 core.sandbox.run_python_code，與 workflow code 節點共用
    r = await run_python_code(code, inputs)
    return ToolExecResponse(
        success=r["ok"],
        output=r.get("output"),
        text=r.get("raw"),
        elapsed_ms=r["elapsed_ms"],
        error=r.get("error"),
    )


@router.post(
    "/{tool_id}/execute",
    response_model=ApiResponse[ToolExecResponse],
    summary="試跑工具（依 kind 分派）",
)
async def execute_tool(
    tool_id: uuid.UUID,
    body: ToolExecRequest,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    row = await session.execute(
        text(
            "SELECT id, kind, tool_type, config, code, is_enabled FROM tools "
            "WHERE id = :id AND workspace_id = :ws"
        ),
        {"id": str(tool_id), "ws": str(ctx.workspace_id)},
    )
    r = row.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Tool 不存在")
    d = dict(r._mapping)
    if not d["is_enabled"]:
        raise HTTPException(status_code=400, detail="此 Tool 已停用")

    cfg = d["config"]
    if isinstance(cfg, str):
        try: cfg = json.loads(cfg)
        except Exception: cfg = {}

    kind = d["kind"]
    # v5.10.5：tool_type 優先（v2.8 新欄位），fallback kind
    tt = (d.get("tool_type") or kind or "").lower()
    audit = {
        "workspace_id": str(ctx.workspace_id),
        "user_id":      str(ctx.user_id),
        "tool_id":      str(tool_id),
        "kind":         tt,
    }
    try:
        if tt == "http":
            result = await _exec_http(cfg, body.inputs)
        elif tt == "mcp":
            result = await _exec_mcp(cfg, body.inputs)
        elif tt in ("custom", "code"):
            result = await _exec_code(d.get("code") or "", body.inputs)
        elif tt == "shell":
            raise HTTPException(
                status_code=501,
                detail="kind=shell 暫不支援（沙箱另案處理）",
            )
        else:
            raise HTTPException(status_code=400, detail=f"未知 kind: {tt}")
        log.info("tool_exec_ok", **audit, status=result.status, elapsed=result.elapsed_ms)
        return ApiResponse(data=result)
    except HTTPException:
        raise
    except Exception as e:
        log.error("tool_exec_failed", **audit, error=str(e))
        return ApiResponse(data=ToolExecResponse(
            success=False, status=None, elapsed_ms=0, error=str(e),
        ))
