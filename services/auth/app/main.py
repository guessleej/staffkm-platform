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
from staffkm_core.observability import setup_otel, instrument_fastapi
from app.config import settings
from app.utils.migrate import run_alembic_upgrade

log = structlog.get_logger()


class GatewayHeadersMiddleware(BaseHTTPMiddleware):
    """從 Gateway 注入的 X-User-ID / X-User-Roles 標頭恢復 request.state"""
    async def dispatch(self, request: Request, call_next):
        request.state.user_id = request.headers.get("X-User-ID") or None
        request.state.roles = [r for r in request.headers.get("X-User-Roles", "").split(",") if r]
        request.state.tenant_id = request.headers.get("X-Tenant-ID") or None
        return await call_next(request)


# [DEPRECATED in v3.1] 新 schema 改動請走 alembic revision（services/auth/alembic/versions/），
# 不要再加進這個 list。此清單保留純為老 deploy 的 idempotent backstop，v4.0 計畫移除。
_AUTH_BOOTSTRAP_DDL = [
    # v3.0：OIDC SSO 正規欄位（idempotent；既有 deploy 自動補）
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS oidc_sub VARCHAR(256)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS oidc_issuer VARCHAR(256)",
    "CREATE INDEX IF NOT EXISTS idx_users_oidc_sub ON users(oidc_sub) WHERE oidc_sub IS NOT NULL",
    # 遷移：把 v2.x 借用 ldap_dn 存的 oidc:{sub} 搬到 oidc_sub
    "UPDATE users SET oidc_sub = SUBSTRING(ldap_dn FROM 6) WHERE ldap_dn LIKE 'oidc:%' AND oidc_sub IS NULL",
]


async def _run_auth_bootstrap_ddl():
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(settings.DB_URL, pool_size=1, max_overflow=0)
    try:
        for i, stmt in enumerate(_AUTH_BOOTSTRAP_DDL, 1):
            try:
                async with engine.begin() as conn:
                    await conn.execute(text(stmt))
                log.info("auth_bootstrap_ddl_ok", step=i)
            except Exception as e:
                log.warning("auth_bootstrap_ddl_failed", step=i, error=str(e))
    finally:
        await engine.dispose()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_otel(service_name="staffkm-auth")
    init_db(settings.DB_URL)
    await _run_auth_bootstrap_ddl()
    await run_alembic_upgrade()
    log.info("auth_service_ready", ldap_enabled=settings.LDAP_ENABLED, oidc_enabled=settings.OIDC_ENABLED)
    yield


app = FastAPI(title="StaffKM Auth Service", version="1.0.0", lifespan=lifespan)
instrument_fastapi(app, service_name="staffkm-auth")
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
