"""Workspace 路由 — 代理至 Auth Service（多租戶管理 API，RFC-001 Stage 2）"""
from fastapi import APIRouter, Request
from app.config import settings
from app.utils.proxy import proxy_request

router = APIRouter()
BASE = settings.AUTH_SERVICE_URL


@router.api_route("/{path:path}", methods=["GET", "POST", "PATCH", "DELETE"])
async def proxy_workspaces(request: Request, path: str):
    """轉發 /workspaces /workspaces/{id} /workspaces/{id}/members 等。"""
    return await proxy_request(request, f"{BASE}/api/v1/workspaces/{path}")


@router.api_route("", methods=["GET", "POST"])
async def proxy_workspaces_root(request: Request):
    """處理沒帶 path 的根請求 (list / create)。"""
    return await proxy_request(request, f"{BASE}/api/v1/workspaces")
