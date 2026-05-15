"""知識庫路由 — 代理至 Knowledge Service"""
from fastapi import APIRouter, Request
from app.config import settings
from app.utils.proxy import proxy_request

router = APIRouter()
BASE = settings.KNOWLEDGE_SERVICE_URL


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_knowledge(request: Request, path: str):
    return await proxy_request(request, f"{BASE}/api/v1/knowledge/{path}")
