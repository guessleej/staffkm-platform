"""API Key 管理路由 — 代理至 Agent Service"""
from fastapi import APIRouter, Request
from app.config import settings
from app.utils.proxy import proxy_request

router = APIRouter()
BASE = settings.AGENT_SERVICE_URL


@router.api_route("", methods=["GET", "POST"])
async def proxy_api_keys_root(request: Request):
    return await proxy_request(request, f"{BASE}/api/v1/api-keys")


@router.api_route("/{path:path}", methods=["GET", "POST", "PATCH", "DELETE"])
async def proxy_api_keys(request: Request, path: str):
    return await proxy_request(request, f"{BASE}/api/v1/api-keys/{path}")
