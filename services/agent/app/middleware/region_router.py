"""Region routing middleware — v5.0 K (active-active scaffolding).

L1 strategy: 每個 workspace 綁一個 primary region；寫請求若打到非 primary
region 的 instance → 回 308 Permanent Redirect 到 primary region URL。
讀請求（GET/HEAD/OPTIONS）一律放過（local replica 已足）。

env：
- REGION_ID           : 這個 instance 自己的 region id（預設 'default'）
- REGION_<X>_URL      : region X 的 public base URL（X 是 region id upper、
                        dash → underscore）。例：us-east-1 → REGION_US_EAST_1_URL
- MULTI_REGION_ENABLED: 'true' 才會在 main.py 把 middleware 註冊起來

設計選擇：
- workspace.primary_region 從 DB 查、process-local cache 5 min（避免每個 request 查）
- workspace 取得來源：X-Workspace-ID header 優先，再 fallback 從 URL `/workspace/{id}/` 抽
- 'default' 視同未設、不 redirect（保持 v4.x 行為）
- 找不到 redirect target URL 時回 503，不靜默 fallback（避免寫到錯 region）
"""
from __future__ import annotations
import os
import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from staffkm_core.utils import database as _db

log = structlog.get_logger()

THIS_REGION = os.environ.get("REGION_ID", "default")
_CACHE_TTL_SEC = 300

# in-process cache：workspace_id → (primary_region, ts)
_workspace_region_cache: dict[str, tuple[str, float]] = {}


def _region_env_key(region_id: str) -> str:
    """region id → env var name. 'us-east-1' → 'REGION_US_EAST_1_URL'."""
    return f"REGION_{region_id.upper().replace('-', '_')}_URL"


async def _lookup_primary_region(workspace_id: str) -> str | None:
    """從 workspace 表查 primary_region，process-local cache 5 min。"""
    now = time.time()
    cached = _workspace_region_cache.get(workspace_id)
    if cached and (now - cached[1] < _CACHE_TTL_SEC):
        return cached[0]

    if _db._session_factory is None:
        return None
    try:
        from sqlalchemy import text
        async with _db._session_factory() as session:
            r = await session.execute(
                text("SELECT primary_region FROM workspace WHERE id = :id"),
                {"id": workspace_id},
            )
            row = r.fetchone()
            region = row.primary_region if row else None
            if region:
                _workspace_region_cache[workspace_id] = (region, now)
            return region
    except Exception as e:
        log.warning("region_lookup_failed", workspace=workspace_id[:8], error=str(e))
        return None


def _extract_workspace_id(request: Request) -> str | None:
    ws_id = request.headers.get("x-workspace-id")
    if ws_id:
        return ws_id
    path = request.url.path
    if "/workspace/" in path:
        parts = path.split("/workspace/", 1)
        if len(parts) > 1:
            return parts[1].split("/", 1)[0] or None
    return None


class RegionRouterMiddleware(BaseHTTPMiddleware):
    """L1: 寫操作必須 routed 到 workspace primary region。"""

    async def dispatch(self, request: Request, call_next):
        # 只攔寫操作
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return await call_next(request)

        # 跳過 webhook / 系統 endpoint（這類本來就是 region-local consumer）
        path = request.url.path
        if "/webhooks/" in path or "/public/billing" in path \
           or path.endswith("/metrics") or path.endswith("/health"):
            return await call_next(request)

        ws_id = _extract_workspace_id(request)
        if not ws_id:
            return await call_next(request)  # 無 workspace context → 不攔

        primary = await _lookup_primary_region(ws_id)
        if not primary or primary == "default" or primary == THIS_REGION:
            return await call_next(request)

        # 跨 region：找 target URL
        target = os.environ.get(_region_env_key(primary))
        if not target:
            log.error(
                "region_redirect_misconfigured",
                workspace=ws_id[:8], primary=primary,
                env_key=_region_env_key(primary),
            )
            return JSONResponse(
                status_code=503,
                content={
                    "error": "region_misconfigured",
                    "primary_region": primary,
                    "message": (
                        f"workspace primary region '{primary}' has no public URL "
                        f"configured (env {_region_env_key(primary)})"
                    ),
                },
            )

        redirect_url = f"{target.rstrip('/')}{path}"
        if request.url.query:
            redirect_url = f"{redirect_url}?{request.url.query}"

        log.info(
            "region_redirect",
            workspace=ws_id[:8],
            this_region=THIS_REGION, primary=primary,
            method=request.method,
        )
        return JSONResponse(
            status_code=308,
            content={
                "error": "region_redirect",
                "primary_region": primary,
                "redirect_to": redirect_url,
                "message": (
                    "Write operations must go to workspace primary region "
                    "(L1 region-pin policy)"
                ),
            },
            headers={"Location": redirect_url},
        )
