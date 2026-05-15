"""外部整合路由 — LINE / Teams / ERP"""
from fastapi import APIRouter, Request
from app.config import settings
from app.utils.proxy import proxy_request

router = APIRouter()
BASE = settings.INTEGRATION_SERVICE_URL


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_integration(request: Request, path: str):
    return await proxy_request(request, f"{BASE}/api/v1/integrations/{path}")
