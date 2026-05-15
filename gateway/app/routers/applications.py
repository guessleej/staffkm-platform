"""Application Builder 路由 — 代理至 Agent Service"""
from fastapi import APIRouter, Request
from app.config import settings
from app.utils.proxy import proxy_request

router = APIRouter()
BASE = settings.AGENT_SERVICE_URL


@router.api_route("", methods=["GET", "POST"])
async def proxy_applications_root(request: Request):
    return await proxy_request(request, f"{BASE}/api/v1/applications")


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_applications(request: Request, path: str):
    is_stream = "chat" in path
    return await proxy_request(request, f"{BASE}/api/v1/applications/{path}", stream=is_stream)
