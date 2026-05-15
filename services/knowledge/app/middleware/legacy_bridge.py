"""LegacyURLBridge — 把 v1 路徑（無 workspace）自動重寫為 default workspace 路徑。

過渡期專用，6 個月後跟舊 endpoint 一併移除。
回應會帶 Deprecation 與 Sunset header，供 client 偵測並逐步遷移。
"""
import structlog
from starlette.middleware.base import BaseHTTPMiddleware

log = structlog.get_logger()

# 與 0001_workspace.sql 內 bootstrap 的 default workspace 相同
DEFAULT_WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"

_LEGACY_PREFIXES = (
    "/api/v1/knowledge/",
    "/api/v1/knowledge",      # 不帶 trailing slash 的根
)


class LegacyURLBridge(BaseHTTPMiddleware):
    """攔截 v1 URL，內部改寫為 v2 workspace-scoped；回應加 Deprecation header。"""

    async def dispatch(self, request, call_next):
        path = request.url.path

        # 已經是 workspace-scoped → 直接放行
        if "/workspace/" in path:
            return await call_next(request)

        # 不是 knowledge service 的關注路徑 → 放行
        if not any(path == p.rstrip("/") or path.startswith(p) for p in _LEGACY_PREFIXES):
            return await call_next(request)

        # 重寫：/api/v1/knowledge/... → /api/v1/workspace/{default}/knowledge/...
        new_path = path.replace(
            "/api/v1/knowledge",
            f"/api/v1/workspace/{DEFAULT_WORKSPACE_ID}/knowledge",
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
