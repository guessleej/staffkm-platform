"""StaffKM API Gateway - 行政知識管理系統 API 閘道"""
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.middleware.auth import AuthMiddleware
from app.middleware.logging import StructuredLoggingMiddleware
from app.middleware.rate_limit import setup_rate_limiter
from app.routers import health, knowledge, agent, auth, chat, integration, admin, applications, api_keys, public

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("staffkm_gateway_starting", version=settings.VERSION)
    yield
    log.info("staffkm_gateway_stopped")


app = FastAPI(
    title="StaffKM API Gateway",
    description="行政人員知識管理系統 - API 閘道",
    version=settings.VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 自訂 Middleware
app.add_middleware(StructuredLoggingMiddleware)
app.add_middleware(AuthMiddleware)

# 速率限制
setup_rate_limiter(app)

# Prometheus 監控
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# 路由註冊
app.include_router(health.router, prefix="/api/v1", tags=["健康檢查"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["身分驗證"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["知識庫管理"])
# 同一個 router 也接 workspace-scoped 路徑（RFC-001 Stage 2）
app.include_router(knowledge.router, prefix="/api/v1/workspace/{workspace_id}/knowledge", tags=["知識庫管理（workspace）"])
app.include_router(agent.router, prefix="/api/v1/agents", tags=["AI 代理人"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["對話管理"])
app.include_router(integration.router, prefix="/api/v1/integrations", tags=["外部整合"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["系統管理"])
app.include_router(applications.router, prefix="/api/v1/applications", tags=["Application Builder"])
app.include_router(api_keys.router, prefix="/api/v1/api-keys", tags=["API Key 管理"])
app.include_router(public.router, prefix="/api/v1/public/applications", tags=["公開存取"])
