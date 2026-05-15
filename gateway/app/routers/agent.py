"""AI 代理人路由 — 代理至 Agent Service"""
from fastapi import APIRouter, Request
from app.config import settings
from app.utils.proxy import proxy_request

router = APIRouter()
BASE = settings.AGENT_SERVICE_URL


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_agent(request: Request, path: str):
    # 串流對話使用 stream=True
    is_stream = request.query_params.get("stream", "false").lower() == "true"
    return await proxy_request(request, f"{BASE}/api/v1/agents/{path}", stream=is_stream)
