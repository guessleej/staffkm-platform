"""知識庫路由 — 透明代理至 Knowledge Service。

v4.0 後 knowledge service 拔 LegacyURLBridge，只接 workspace-scoped:
  - /api/v1/workspace/{ws_id}/knowledge/...

v5.9.16: 加 X-Workspace-ID header 注入到 path（跟 agent / chat 對齊）。
"""
from fastapi import APIRouter, Request

from app.config import settings
from app.utils.proxy import proxy_request

router = APIRouter()
BASE = settings.KNOWLEDGE_SERVICE_URL


@router.api_route("", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
@router.api_route("/", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_knowledge_root(request: Request):
    return await proxy_knowledge(request, "")


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_knowledge(request: Request, path: str):
    """注入 X-Workspace-ID 成 workspace-scoped path；本身已是 workspace 路徑 (gateway
    main.py 也 mount 在 /api/v1/workspace/{ws}/knowledge) 則 request.url.path 已含
    workspace，直接轉發即可。"""
    incoming_path = request.url.path
    if incoming_path.startswith("/api/v1/workspace/"):
        # 已是 workspace-scoped，原樣轉發
        target = f"{BASE}{incoming_path}"
    else:
        ws = request.headers.get("X-Workspace-ID")
        suffix = f"/{path}" if path else ""
        if ws:
            target = f"{BASE}/api/v1/workspace/{ws}/knowledge{suffix}"
        else:
            # 沒帶 workspace header → 退回 legacy (knowledge 沒接會 404)
            target = f"{BASE}/api/v1/knowledge{suffix}"
    return await proxy_request(request, target)
