"""公開路由 — 不需 JWT 驗證"""
from fastapi import APIRouter, Request
from app.config import settings
from app.utils.proxy import proxy_request

router = APIRouter()
BASE = settings.AGENT_SERVICE_URL


@router.api_route("/{app_id}", methods=["GET"])
async def public_app_info(request: Request, app_id: str):
    return await proxy_request(request, f"{BASE}/api/v1/public/applications/{app_id}")


@router.api_route("/{app_id}/chat", methods=["POST"])
async def public_app_chat(request: Request, app_id: str):
    return await proxy_request(request, f"{BASE}/api/v1/public/applications/{app_id}/chat", stream=True)
