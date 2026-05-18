"""Idempotency-Key middleware — v3.6 P3。

只攔截：method=POST + 有 Idempotency-Key header + 非 SSE endpoint。

第一次：跑 handler、capture response body → 寫 idempotency_keys row
第二次（同 key+endpoint 在 24h 內）：直接回原 response，不跑 handler

設計選擇：
- key 範圍：global per workspace（key + endpoint，cross-user 仍 hit）
- TTL：24h（DB column default 自動）
- SSE / streaming：透過 content-type / accept header 偵測，跳過
- response_json：JSON body cache（非 JSON response 不快取）
"""
from __future__ import annotations
import json as _json

import structlog
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from starlette.requests import Request

from staffkm_core.utils import database as _db

log = structlog.get_logger()


def _is_streaming(request: Request) -> bool:
    """SSE 或明顯 streaming endpoint 不快取（response body 不是 single block）。"""
    accept = request.headers.get("accept", "")
    if "text/event-stream" in accept:
        return True
    path = request.url.path
    # streaming endpoint 路徑特徵
    if any(seg in path for seg in ("/chat", "/stream", "/sse", "/run")):
        return True
    return False


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """同 Idempotency-Key + endpoint 24h 內 cache response。"""

    async def dispatch(self, request: Request, call_next):
        # 只攔 POST + 有 header
        if request.method != "POST":
            return await call_next(request)
        idem_key = request.headers.get("idempotency-key") or request.headers.get("Idempotency-Key")
        if not idem_key:
            return await call_next(request)
        if _is_streaming(request):
            return await call_next(request)

        endpoint = request.url.path[:128]
        key = idem_key[:128]

        if _db._session_factory is None:
            # DB 未 init（unit test / startup race）→ degrade 跑 handler
            return await call_next(request)

        # Lookup
        try:
            async with _db._session_factory() as session:
                r = await session.execute(text("""
                    SELECT response_json, status_code FROM idempotency_keys
                    WHERE key=:k AND endpoint=:e AND expires_at > now()
                """), {"k": key, "e": endpoint})
                row = r.fetchone()
                if row:
                    log.info("idempotency_hit", key=key[:16], endpoint=endpoint)
                    return JSONResponse(
                        content=row[0],
                        status_code=row[1] or 200,
                        headers={"Idempotency-Replayed": "true"},
                    )
        except Exception as e:
            log.warning("idempotency_lookup_failed", error=str(e))
            return await call_next(request)

        # Run handler
        response = await call_next(request)

        # Capture body only if JSON + 2xx
        ctype = response.headers.get("content-type", "")
        if not ctype.startswith("application/json"):
            return response
        if response.status_code >= 500:
            return response  # 5xx 不快取（client 應 retry）

        # 收集 body chunks（async iterator）
        body_chunks: list[bytes] = []
        async for chunk in response.body_iterator:
            body_chunks.append(chunk)
        body_bytes = b"".join(body_chunks)
        try:
            body_json = _json.loads(body_bytes.decode("utf-8"))
        except Exception:
            # 非 valid JSON → 不快取
            return Response(
                content=body_bytes, status_code=response.status_code,
                headers=dict(response.headers), media_type=ctype,
            )

        # Persist
        try:
            ws_id = request.headers.get("x-workspace-id") or None
            async with _db._session_factory() as session:
                await session.execute(text("""
                    INSERT INTO idempotency_keys (key, endpoint, workspace_id, response_json, status_code)
                    VALUES (:k, :e, :ws, CAST(:rj AS jsonb), :sc)
                    ON CONFLICT (key, endpoint) DO NOTHING
                """), {
                    "k": key, "e": endpoint, "ws": ws_id,
                    "rj": _json.dumps(body_json, ensure_ascii=False, default=str),
                    "sc": response.status_code,
                })
                await session.commit()
            log.info("idempotency_stored", key=key[:16], endpoint=endpoint, status=response.status_code)
        except Exception as e:
            log.warning("idempotency_store_failed", error=str(e))

        # 重組 response 回傳給 client
        return Response(
            content=body_bytes, status_code=response.status_code,
            headers=dict(response.headers), media_type=ctype,
        )
