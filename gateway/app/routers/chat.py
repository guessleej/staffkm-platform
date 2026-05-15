"""對話路由 — 代理至 Chat Service，支援 SSE 串流"""
from fastapi import APIRouter, Request
from app.config import settings
from app.utils.proxy import proxy_request

router = APIRouter()
BASE = settings.CHAT_SERVICE_URL


@router.api_route("/{path:path}", methods=["GET", "POST", "DELETE"])
async def proxy_chat(request: Request, path: str):
    is_stream = "stream" in path or request.query_params.get("stream") == "true"
    return await proxy_request(
        request, f"{BASE}/api/v1/chat/{path}", timeout=120.0, stream=is_stream
    )
