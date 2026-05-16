"""LegacyURLBridge — 把 v1 路徑（無 workspace）自動重寫為 default workspace 路徑。

過渡期專用，6 個月後（2026-11-15）跟舊 endpoint 一併移除。
回應會帶 Deprecation 與 Sunset header，供 client 偵測並逐步遷移。

涵蓋路徑：
  /api/v1/agents/...        → /api/v1/workspace/{default}/agents/...
  /api/v1/applications/...  → /api/v1/workspace/{default}/applications/...
  /api/v1/api-keys/...      → /api/v1/workspace/{default}/api-keys/...

排除：
  /api/v1/public/applications/...   公開存取，不需 workspace
"""
import structlog
from starlette.middleware.base import BaseHTTPMiddleware

log = structlog.get_logger()

# 與 0001_workspace.sql 內 bootstrap 的 default workspace 相同
DEFAULT_WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"

_LEGACY_PREFIXES = (
    "/api/v1/agents",
    "/api/v1/applications",
    "/api/v1/api-keys",
    "/api/v1/projects",
)

# 不重寫的例外 path（公開存取或 pre-auth endpoint）
_EXCLUDE_PREFIXES = (
    "/api/v1/public/",
    "/api/v1/api-keys/verify",   # API key 驗證本身免登入，不需 workspace
)


class LegacyURLBridge(BaseHTTPMiddleware):
    """攔截 v1 URL，內部改寫為 v2 workspace-scoped；回應加 Deprecation header。"""

    async def dispatch(self, request, call_next):
        path = request.url.path

        # 已經是 workspace-scoped → 直接放行
        if "/workspace/" in path:
            return await call_next(request)

        # 在排除清單 → 放行
        if any(path.startswith(p) for p in _EXCLUDE_PREFIXES):
            return await call_next(request)

        # 找出符合的 legacy prefix
        matched: str | None = None
        for prefix in _LEGACY_PREFIXES:
            if path == prefix or path.startswith(prefix + "/"):
                matched = prefix
                break
        if matched is None:
            return await call_next(request)

        # 重寫：/api/v1/{group}/...  →  /api/v1/workspace/{default}/{group}/...
        suffix = matched.replace("/api/v1/", "", 1)  # e.g. "agents"
        new_path = path.replace(
            matched,
            f"/api/v1/workspace/{DEFAULT_WORKSPACE_ID}/{suffix}",
            1,
        )
        log.debug("legacy_url_rewritten", from_=path, to=new_path)

        request.scope["path"] = new_path
        request.scope["raw_path"] = new_path.encode("utf-8")

        response = await call_next(request)
        response.headers["Deprecation"] = "true"
        response.headers["Sunset"] = "Wed, 15 Nov 2026 00:00:00 GMT"
        response.headers["Link"] = f'<{new_path}>; rel="successor-version"'
        return response
