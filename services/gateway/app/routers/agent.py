"""AI 代理人路由 — 代理至 Agent Service

v5.9.10: v4.0 拔 LegacyURLBridge 後，agent service 只接 workspace-scoped 路徑。
這個 router 之前直接 forward /api/v1/agents/{path} → 404。
改成讀 X-Workspace-ID header 注入 workspace prefix。
"""
from fastapi import APIRouter, Request
from app.config import settings
from app.utils.proxy import proxy_request

router = APIRouter()
BASE = settings.AGENT_SERVICE_URL


def _target_url(request: Request, suffix: str = "") -> str:
    ws = request.headers.get("X-Workspace-ID")
    if ws:
        base_path = f"/api/v1/workspace/{ws}/agents"
    else:
        # 沒帶 workspace header → 退回 legacy（agent 沒接會 404，但保留語意）
        base_path = "/api/v1/agents"
    return f"{BASE}{base_path}{suffix}"


@router.api_route("", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@router.api_route("/", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_agent_root(request: Request):
    is_stream = request.query_params.get("stream", "false").lower() == "true"
    return await proxy_request(request, _target_url(request), stream=is_stream)


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_agent(request: Request, path: str):
    # /chat 是 SSE 串流端點
    is_stream = "chat" in path or request.query_params.get("stream", "false").lower() == "true"
    suffix = f"/{path}" if path else ""
    return await proxy_request(request, _target_url(request, suffix), stream=is_stream)
