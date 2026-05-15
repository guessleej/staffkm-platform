"""系統管理路由 — 聚合各服務管理端點"""
from fastapi import APIRouter, Request, Depends
from app.config import settings
from app.utils.proxy import proxy_request

router = APIRouter()


def require_admin(request: Request):
    roles = getattr(request.state, "roles", [])
    if "admin" not in roles:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="需要管理員權限")


@router.api_route("/knowledge/{path:path}", methods=["GET", "POST", "PUT", "DELETE"],
                  dependencies=[Depends(require_admin)])
async def admin_knowledge(request: Request, path: str):
    return await proxy_request(request, f"{settings.KNOWLEDGE_SERVICE_URL}/api/v1/admin/knowledge/{path}")


@router.api_route("/users/{path:path}", methods=["GET", "POST", "PUT", "DELETE"],
                  dependencies=[Depends(require_admin)])
async def admin_users(request: Request, path: str):
    return await proxy_request(request, f"{settings.AUTH_SERVICE_URL}/api/v1/admin/users/{path}")


@router.api_route("/agents/{path:path}", methods=["GET", "POST", "PUT", "DELETE"],
                  dependencies=[Depends(require_admin)])
async def admin_agents(request: Request, path: str):
    return await proxy_request(request, f"{settings.AGENT_SERVICE_URL}/api/v1/admin/agents/{path}")


@router.api_route("/models/{path:path}", methods=["GET", "POST", "PUT", "DELETE"],
                  dependencies=[Depends(require_admin)])
async def admin_models(request: Request, path: str):
    return await proxy_request(request, f"{settings.AUTH_SERVICE_URL}/api/v1/admin/models/{path}")
