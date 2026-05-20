"""Project 路由 — 代理至 Agent Service（RFC-006 Phase C-1）

v5.9.17: agent service v4.0 後只接 workspace-scoped /api/v1/workspace/{ws}/projects/...
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
        return f"{BASE}/api/v1/workspace/{ws}/projects{suffix}"
    return f"{BASE}/api/v1/projects{suffix}"


@router.api_route("", methods=["GET", "POST"])
@router.api_route("/", methods=["GET", "POST"])
async def proxy_projects_root(request: Request):
    return await proxy_request(request, _target(request))


@router.api_route("/{path:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE"])
async def proxy_projects(request: Request, path: str):
    suffix = f"/{path}" if path else ""
    return await proxy_request(request, _target(request, suffix))
