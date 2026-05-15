"""身分驗證路由 — 代理至 Auth Service"""
from fastapi import APIRouter, Request
from app.config import settings
from app.utils.proxy import proxy_request

router = APIRouter()
BASE = settings.AUTH_SERVICE_URL


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_auth(request: Request, path: str):
    return await proxy_request(request, f"{BASE}/api/v1/auth/{path}")
