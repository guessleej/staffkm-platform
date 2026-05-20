"""API Key 管理路由 — 代理至 Agent Service

v5.9.17: agent service v4.0 後 CRUD 端點走 workspace-scoped
  /api/v1/workspace/{ws}/api-keys/...
但 /api/v1/api-keys 還有 public_router (給外部 client 驗證 API key，無 auth)。
有 X-Workspace-ID → 注入 workspace；沒帶 → 退回 legacy（命中 public_router）。
"""
from fastapi import APIRouter, Request
from app.config import settings
from app.utils.proxy import proxy_request

router = APIRouter()
BASE = settings.AGENT_SERVICE_URL


def _target(request: Request, suffix: str = "") -> str:
    ws = request.headers.get("X-Workspace-ID")
    if ws:
        return f"{BASE}/api/v1/workspace/{ws}/api-keys{suffix}"
    return f"{BASE}/api/v1/api-keys{suffix}"


@router.api_route("", methods=["GET", "POST"])
@router.api_route("/", methods=["GET", "POST"])
async def proxy_api_keys_root(request: Request):
    return await proxy_request(request, _target(request))


@router.api_route("/{path:path}", methods=["GET", "POST", "PATCH", "DELETE"])
async def proxy_api_keys(request: Request, path: str):
    suffix = f"/{path}" if path else ""
    return await proxy_request(request, _target(request, suffix))
