"""MCP Hub API（M4 啟動）。

- GET    /mcp/servers                    列出 workspace 內 mcp servers
- POST   /mcp/servers                    新增（require_writer）
- PUT    /mcp/servers/{id}               更新
- DELETE /mcp/servers/{id}               刪除
- POST   /mcp/servers/{id}/refresh       重抓 tools 並寫入 mcp_tools_cache
- GET    /mcp/servers/{id}/tools         列出該 server 已快取的 tools
- POST   /mcp/servers/{id}/call          呼叫指定 tool（require_writer）
"""
from __future__ import annotations

import json as _json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.mcp_client import MCPClient
from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_member, require_writer

router = APIRouter()


_VALID_TRANSPORTS = ("http", "sse", "stdio")


class ServerCreate(BaseModel):
    name:        str  = Field(..., min_length=1, max_length=128)
    description: str | None = None
    transport:   str = "http"
    url:         str | None = None
    command:     str | None = None
    args:        list[str] = Field(default_factory=list)
    env:         dict[str, str] = Field(default_factory=dict)
    enabled:     bool = True


class ServerUpdate(BaseModel):
    name:        str | None = None
    description: str | None = None
    url:         str | None = None
    enabled:     bool | None = None


class CallToolRequest(BaseModel):
    tool:      str
    arguments: dict[str, Any] = Field(default_factory=dict)


def _validate(create: ServerCreate) -> None:
    if create.transport not in _VALID_TRANSPORTS:
        raise HTTPException(status_code=400, detail=f"transport 必須為 {_VALID_TRANSPORTS}")
    if create.transport in ("http", "sse") and not create.url:
        raise HTTPException(status_code=400, detail="http / sse transport 須提供 url")
    if create.transport == "stdio":
        raise HTTPException(status_code=501, detail="stdio transport 留給 M4 中段；本階段請用 http / sse")


@router.get("/servers", response_model=ApiResponse, summary="列出 MCP servers")
async def list_servers(
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    rows = await session.execute(
        text(
            """
            SELECT id, name, description, transport, url, enabled,
                   last_refreshed_at, last_error, created_at, updated_at
            FROM mcp_servers
            WHERE workspace_id = :ws
            ORDER BY created_at DESC
            """
        ),
        {"ws": str(ctx.workspace_id)},
    )
    return ApiResponse(data=[dict(r._mapping) for r in rows.fetchall()])


@router.post("/servers", response_model=ApiResponse, summary="新增 MCP server")
async def create_server(
    body: ServerCreate,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    _validate(body)
    sid = str(uuid.uuid4())
    await session.execute(
        text(
            """
            INSERT INTO mcp_servers (
                id, workspace_id, name, description, transport, url, command, args, env, enabled, created_by
            ) VALUES (
                :id, :ws, :name, :desc, :tr, :url, :cmd, :args::jsonb, :env::jsonb, :en, :by
            )
            """
        ),
        {
            "id":   sid,
            "ws":   str(ctx.workspace_id),
            "name": body.name,
            "desc": body.description,
            "tr":   body.transport,
            "url":  body.url,
            "cmd":  body.command,
            "args": _json.dumps(body.args, ensure_ascii=False),
            "env":  _json.dumps(body.env, ensure_ascii=False),
            "en":   body.enabled,
            "by":   str(ctx.user_id) if ctx.user_id else None,
        },
    )
    return ApiResponse(data={"id": sid}, message="MCP server 已建立")


@router.put("/servers/{server_id}", response_model=ApiResponse, summary="更新 MCP server")
async def update_server(
    server_id: uuid.UUID,
    body: ServerUpdate,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    sets = ["updated_at = now()"]
    params: dict[str, Any] = {"id": str(server_id), "ws": str(ctx.workspace_id)}
    for col, val in body.dict(exclude_unset=True).items():
        sets.append(f"{col} = :{col}")
        params[col] = val
    if len(sets) == 1:
        return ApiResponse(message="no-op")
    sql = f"UPDATE mcp_servers SET {', '.join(sets)} WHERE id = :id AND workspace_id = :ws"
    res = await session.execute(text(sql), params)
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="server 不存在")
    return ApiResponse(message="MCP server 已更新")


@router.delete("/servers/{server_id}", response_model=ApiResponse, summary="刪除 MCP server")
async def delete_server(
    server_id: uuid.UUID,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(
        text("DELETE FROM mcp_tools_cache WHERE server_id = :id AND workspace_id = :ws"),
        {"id": str(server_id), "ws": str(ctx.workspace_id)},
    )
    res = await session.execute(
        text("DELETE FROM mcp_servers WHERE id = :id AND workspace_id = :ws"),
        {"id": str(server_id), "ws": str(ctx.workspace_id)},
    )
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="server 不存在")
    return ApiResponse(message="MCP server 已刪除")


async def _get_server(session, server_id, ws):
    r = await session.execute(
        text(
            "SELECT id, transport, url, enabled FROM mcp_servers "
            "WHERE id = :id AND workspace_id = :ws"
        ),
        {"id": str(server_id), "ws": str(ws)},
    )
    row = r.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="server 不存在")
    return dict(row._mapping)


@router.post("/servers/{server_id}/refresh", response_model=ApiResponse, summary="重抓 tools")
async def refresh_tools(
    server_id: uuid.UUID,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    srv = await _get_server(session, server_id, ctx.workspace_id)
    if srv["transport"] not in ("http", "sse"):
        raise HTTPException(status_code=501, detail="只支援 http / sse")

    client = MCPClient(srv["url"])
    try:
        tools = await client.list_tools()
    except Exception as e:
        await session.execute(
            text("UPDATE mcp_servers SET last_error = :err, updated_at = now() "
                 "WHERE id = :id AND workspace_id = :ws"),
            {"err": str(e)[:512], "id": str(server_id), "ws": str(ctx.workspace_id)},
        )
        raise HTTPException(status_code=502, detail=f"連線失敗：{e}") from e
    finally:
        await client.aclose()

    # 重寫 cache
    await session.execute(
        text("DELETE FROM mcp_tools_cache WHERE server_id = :id AND workspace_id = :ws"),
        {"id": str(server_id), "ws": str(ctx.workspace_id)},
    )
    for t in tools:
        await session.execute(
            text(
                """
                INSERT INTO mcp_tools_cache (
                    id, server_id, workspace_id, name, description, input_schema
                ) VALUES (
                    :id, :sid, :ws, :n, :d, :schema::jsonb
                )
                """
            ),
            {
                "id":     str(uuid.uuid4()),
                "sid":    str(server_id),
                "ws":     str(ctx.workspace_id),
                "n":      t.get("name", ""),
                "d":      t.get("description"),
                "schema": _json.dumps(t.get("inputSchema") or t.get("input_schema") or {}, ensure_ascii=False),
            },
        )

    await session.execute(
        text("UPDATE mcp_servers SET last_refreshed_at = :now, last_error = NULL, updated_at = :now "
             "WHERE id = :id AND workspace_id = :ws"),
        {"now": datetime.utcnow(), "id": str(server_id), "ws": str(ctx.workspace_id)},
    )
    return ApiResponse(data={"count": len(tools)}, message="tools 已重抓")


@router.get("/servers/{server_id}/tools", response_model=ApiResponse, summary="列出已快取 tools")
async def list_cached_tools(
    server_id: uuid.UUID,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    rows = await session.execute(
        text(
            """
            SELECT id, name, description, input_schema, refreshed_at
            FROM mcp_tools_cache
            WHERE server_id = :id AND workspace_id = :ws
            ORDER BY name
            """
        ),
        {"id": str(server_id), "ws": str(ctx.workspace_id)},
    )
    return ApiResponse(data=[dict(r._mapping) for r in rows.fetchall()])


@router.post("/servers/{server_id}/call", response_model=ApiResponse, summary="呼叫 tool")
async def call_tool(
    server_id: uuid.UUID,
    body: CallToolRequest,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    srv = await _get_server(session, server_id, ctx.workspace_id)
    if not srv["enabled"]:
        raise HTTPException(status_code=400, detail="server 已停用")
    client = MCPClient(srv["url"])
    try:
        return ApiResponse(data=await client.call_tool(body.tool, body.arguments))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    finally:
        await client.aclose()
