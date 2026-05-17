"""Auth Service — 身分驗證服務 (本地 + LDAP/AD)"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from app.api.auth import router as auth_router
from app.api.oidc import router as oidc_router
from app.api.users import router as users_router
from app.api.models import router as models_router
from app.api.workspaces import router as workspaces_router
from staffkm_core.utils.database import init_db
from app.config import settings

log = structlog.get_logger()


class GatewayHeadersMiddleware(BaseHTTPMiddleware):
    """從 Gateway 注入的 X-User-ID / X-User-Roles 標頭恢復 request.state"""
    async def dispatch(self, request: Request, call_next):
        request.state.user_id = request.headers.get("X-User-ID") or None
        request.state.roles = [r for r in request.headers.get("X-User-Roles", "").split(",") if r]
        request.state.tenant_id = request.headers.get("X-Tenant-ID") or None
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(settings.DB_URL)
    log.info("auth_service_ready", ldap_enabled=settings.LDAP_ENABLED)
    yield


app = FastAPI(title="StaffKM Auth Service", version="1.0.0", lifespan=lifespan)
# Prometheus /metrics — v2.2
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

app.add_middleware(GatewayHeadersMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["身分驗證"])
app.include_router(oidc_router, prefix="/api/v1/auth/oidc", tags=["OIDC SSO (v2.4-B)"])
app.include_router(users_router, prefix="/api/v1/admin/users", tags=["使用者管理"])
app.include_router(models_router, prefix="/api/v1/admin/models", tags=["模型供應商管理"])
app.include_router(workspaces_router, prefix="/api/v1/workspaces", tags=["工作區（多租戶）"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "auth"}
