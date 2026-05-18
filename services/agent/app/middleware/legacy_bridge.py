"""LegacyURLBridge — v3.1 起預設 410 Gone。

v2.x：把 v1 URL 自動重寫為 v2 workspace-scoped URL。
v3.0：保留 bridge 但提供 410 模式（default 仍 rewrite，因 gateway/frontend 還在用 v1 URL）。
v3.1：（本檔）gateway proxy + frontend axios 都已自動注入 workspace_id，
       預設翻成 410 — bridge 只擋未遷移的 SDK / custom client。

部署可透過 env `LEGACY_URL_MODE` 控制：
  rewrite    — 舊行為，重寫 v1 → v2 + Deprecation header（用 hardcoded DEFAULT_WORKSPACE_ID，等於假設單租戶，僅作為 backstop）
  410        — v3.1 預設，直接 410 + Link header 指 v2 URL
  off        — 完全不攔截（v1 URL 變 404）

升 v3.1 後建議監控有沒有 unexpected 410（log 標籤 `legacy_url_blocked_410`）。
若仍有舊 client 無法即時遷移可暫時 `LEGACY_URL_MODE=rewrite` 回滾；v4.0 將拔除本中介層。
"""
from __future__ import annotations

import os

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

log = structlog.get_logger()

DEFAULT_WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"
SUNSET_DATE = "Wed, 15 Nov 2026 00:00:00 GMT"

_LEGACY_PREFIXES = (
    "/api/v1/agents",
    "/api/v1/applications",
    "/api/v1/api-keys",
    "/api/v1/projects",
    "/api/v1/tools",
    "/api/v1/skills",
    "/api/v1/data-sources",
    "/api/v1/folders",
    "/api/v1/usage",
    "/api/v1/triggers",
    "/api/v1/mcp",
    "/api/v1/memories",
    "/api/v1/model-providers",
    "/api/v1/media-providers",
    "/api/v1/app-templates",
    "/api/v1/admin/audit-logs",
    "/api/v1/user-quotas",
    "/api/v1/quota-alerts",
    "/api/v1/approvals",
    "/api/v1/conversations",
)

_EXCLUDE_PREFIXES = (
    "/api/v1/public/",
    "/api/v1/api-keys/verify",
)


def _v2_url(path: str, matched: str) -> str:
    """組 v2 workspace-scoped URL。"""
    suffix = matched.replace("/api/v1/", "", 1)
    return path.replace(matched, f"/api/v1/workspace/{DEFAULT_WORKSPACE_ID}/{suffix}", 1)


class LegacyURLBridge(BaseHTTPMiddleware):
    """v3.0：依 LEGACY_URL_MODE env 決定行為。"""

    def __init__(self, app):
        super().__init__(app)
        # v3.1：default 翻成 '410' — gateway proxy + frontend axios 已自動注入
        # X-Workspace-ID，正常 caller 不會再進到 bridge。
        # 若有舊 SDK / custom client 暫時無法遷移 → 設 LEGACY_URL_MODE=rewrite 回滾。
        self.mode = os.environ.get("LEGACY_URL_MODE", "410").lower()
        if self.mode not in ("rewrite", "410", "off"):
            log.warning("invalid_legacy_url_mode", mode=self.mode, fallback="rewrite")
            self.mode = "rewrite"
        log.info("legacy_url_bridge_init", mode=self.mode)

    async def dispatch(self, request, call_next):
        path = request.url.path
        if self.mode == "off":
            return await call_next(request)
        if "/workspace/" in path:
            return await call_next(request)
        if any(path.startswith(p) for p in _EXCLUDE_PREFIXES):
            return await call_next(request)

        matched: str | None = None
        for prefix in _LEGACY_PREFIXES:
            if path == prefix or path.startswith(prefix + "/"):
                matched = prefix
                break
        if matched is None:
            return await call_next(request)

        new_url = _v2_url(path, matched)

        if self.mode == "rewrite":
            # v2.x compat：保留舊行為
            log.debug("legacy_url_rewritten", from_=path, to=new_url)
            request.scope["path"] = new_url
            request.scope["raw_path"] = new_url.encode("utf-8")
            resp = await call_next(request)
            resp.headers["Deprecation"] = "true"
            resp.headers["Sunset"] = SUNSET_DATE
            resp.headers["Link"] = f'<{new_url}>; rel="successor-version"'
            return resp

        # v3.0 預設：410 Gone
        log.info("legacy_url_blocked_410", path=path, suggested=new_url)
        return JSONResponse(
            {
                "error": "gone",
                "detail": (
                    "v1 URL endpoints have been retired in v3.0. "
                    "Use the workspace-scoped v2 URL instead."
                ),
                "successor": new_url,
                "sunset": SUNSET_DATE,
                "doc": "https://staffkm.example.com/api/docs",
            },
            status_code=410,
            headers={
                "Sunset": SUNSET_DATE,
                "Link": f'<{new_url}>; rel="successor-version"',
            },
        )
