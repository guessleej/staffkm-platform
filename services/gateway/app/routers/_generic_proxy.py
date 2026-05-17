"""通用 backlog 模組 proxy（RFC-006 新 backlog）— tools / skills / data-sources。

每個模組都走相同的 reverse proxy 模式到 agent service。
"""
from fastapi import APIRouter, Request

from app.config import settings
from app.utils.proxy import proxy_request


def make_proxy_router(prefix: str) -> APIRouter:
    """產生 /api/v1/{prefix}/* → agent service 的 proxy router。"""
    router = APIRouter()
    base = settings.AGENT_SERVICE_URL

    @router.api_route("", methods=["GET", "POST"])
    @router.api_route("/", methods=["GET", "POST"])
    async def proxy_root(request: Request):
        return await proxy_request(request, f"{base}/api/v1/{prefix}")

    @router.api_route("/{path:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE"])
    async def proxy_path(request: Request, path: str):
        if not path:
            return await proxy_request(request, f"{base}/api/v1/{prefix}")
        return await proxy_request(request, f"{base}/api/v1/{prefix}/{path}")

    return router


tools_router        = make_proxy_router("tools")
skills_router       = make_proxy_router("skills")
data_sources_router = make_proxy_router("data-sources")
folders_router      = make_proxy_router("folders")
model_providers_router = make_proxy_router("model-providers")
media_providers_router = make_proxy_router("media-providers")
# Sprint 19 orphan endpoint cleanup
usage_router        = make_proxy_router("usage")
triggers_router     = make_proxy_router("triggers")
mcp_router          = make_proxy_router("mcp")
memories_router     = make_proxy_router("memories")
