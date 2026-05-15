"""知識庫路由 — 透明代理至 Knowledge Service。

接受兩種 path（皆轉發、保留原 path）：
  - /api/v1/knowledge/...                       (legacy v1，後端有 LegacyURLBridge 處理)
  - /api/v1/workspace/{ws_id}/knowledge/...     (v2 workspace-scoped，RFC-001 Stage 2)
"""
from fastapi import APIRouter, Request

from app.config import settings
from app.utils.proxy import proxy_request

router = APIRouter()
BASE = settings.KNOWLEDGE_SERVICE_URL


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_knowledge(request: Request, path: str):
    """整段 request.url.path 直接轉發；後端依路徑自行分流。"""
    return await proxy_request(request, f"{BASE}{request.url.path}")
