"""Project 路由 — 代理至 Agent Service（RFC-006 Phase C-1）"""
from fastapi import APIRouter, Request
from app.config import settings
from app.utils.proxy import proxy_request

router = APIRouter()
BASE = settings.AGENT_SERVICE_URL


@router.api_route("", methods=["GET", "POST"])
@router.api_route("/", methods=["GET", "POST"])
async def proxy_projects_root(request: Request):
    return await proxy_request(request, f"{BASE}/api/v1/projects")


@router.api_route("/{path:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE"])
async def proxy_projects(request: Request, path: str):
    if not path:
        return await proxy_request(request, f"{BASE}/api/v1/projects")
    return await proxy_request(request, f"{BASE}/api/v1/projects/{path}")
