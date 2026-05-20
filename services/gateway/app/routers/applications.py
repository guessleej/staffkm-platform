"""Application Builder 路由 — 代理至 Agent Service

v5.9.17: agent service 自 v4.0 起只接 workspace-scoped 路徑
  /api/v1/workspace/{ws}/applications/...
讀 X-Workspace-ID header 注入 workspace prefix。
"""
from fastapi import APIRouter, Request
from app.config import settings
from app.utils.proxy import proxy_request

router = APIRouter()
BASE = settings.AGENT_SERVICE_URL


def _target(request: Request, suffix: str = "") -> str:
    ws = request.headers.get("X-Workspace-ID")
    if ws:
        return f"{BASE}/api/v1/workspace/{ws}/applications{suffix}"
    return f"{BASE}/api/v1/applications{suffix}"


@router.api_route("", methods=["GET", "POST"])
@router.api_route("/", methods=["GET", "POST"])
async def proxy_applications_root(request: Request):
    return await proxy_request(request, _target(request))


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_applications(request: Request, path: str):
    is_stream = "chat" in path
    suffix = f"/{path}" if path else ""
    return await proxy_request(request, _target(request, suffix), stream=is_stream)
