"""Workspace 路由 — 代理至 Auth Service（多租戶管理 API，RFC-001 Stage 2）"""
from fastapi import APIRouter, Request
from app.config import settings
from app.utils.proxy import proxy_request

router = APIRouter()
BASE = settings.AUTH_SERVICE_URL


# 根路徑 (list / create)：用明確的 "" 與 "/" 兩個別名涵蓋 trailing slash 兩種寫法
@router.api_route("", methods=["GET", "POST"])
@router.api_route("/", methods=["GET", "POST"])
async def proxy_workspaces_root(request: Request):
    return await proxy_request(request, f"{BASE}/api/v1/workspaces")


# 子路徑 (get / update / delete / members)：必須要有後綴內容
@router.api_route("/{path:path}", methods=["GET", "POST", "PATCH", "DELETE"])
async def proxy_workspaces(request: Request, path: str):
    # path 可能為空字串（trailing slash）→ fallthrough 到 root
    if not path:
        return await proxy_request(request, f"{BASE}/api/v1/workspaces")
    return await proxy_request(request, f"{BASE}/api/v1/workspaces/{path}")
