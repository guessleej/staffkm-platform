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
from app.routers import health, knowledge, agent, auth, chat, integration, admin, applications, api_keys, public, workspaces, projects
from app.routers._generic_proxy import (
    tools_router, skills_router, data_sources_router, folders_router,
    model_providers_router, media_providers_router,
    usage_router, triggers_router, mcp_router, memories_router,
    app_templates_router, audit_logs_router, admin_quotas_router,
    user_quotas_router, quota_alerts_router,
)

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
app.include_router(workspaces.router, prefix="/api/v1/workspaces", tags=["工作區（多租戶）"])
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
app.include_router(projects.router, prefix="/api/v1/projects", tags=["Project（RFC-006）"])
app.include_router(tools_router, prefix="/api/v1/tools", tags=["Tool（新 backlog）"])
app.include_router(skills_router, prefix="/api/v1/skills", tags=["Skill（新 backlog）"])
app.include_router(data_sources_router, prefix="/api/v1/data-sources", tags=["Data Source（新 backlog）"])
app.include_router(folders_router, prefix="/api/v1/folders", tags=["Entity Folders（D-5）"])
app.include_router(model_providers_router, prefix="/api/v1/model-providers", tags=["Model Provider Registry（M3）"])
app.include_router(media_providers_router, prefix="/api/v1/media-providers", tags=["Media Provider Registry（M4）"])
# Sprint 19 orphan cleanup — 補上之前漏 mount 的四個模組
app.include_router(usage_router,    prefix="/api/v1/usage",    tags=["Token 用量 + Quota"])
app.include_router(triggers_router, prefix="/api/v1/triggers", tags=["Event Triggers"])
app.include_router(mcp_router,      prefix="/api/v1/mcp",      tags=["MCP Servers"])
app.include_router(memories_router, prefix="/api/v1/memories", tags=["長期記憶"])
app.include_router(app_templates_router, prefix="/api/v1/app-templates", tags=["Workspace App Templates"])
app.include_router(audit_logs_router,    prefix="/api/v1/admin/audit-logs",   tags=["Audit Log (v3.0)"])
# v3.2 P3：admin 跨 workspace quota
app.include_router(admin_quotas_router,  prefix="/api/v1/admin/quotas",       tags=["Admin Quota (v3.2)"])
# v3.3 D1/D2：user-level quota + quota alerts
app.include_router(user_quotas_router,   prefix="/api/v1/user-quotas",        tags=["User Quota (v3.3)"])
app.include_router(quota_alerts_router,  prefix="/api/v1/quota-alerts",       tags=["Quota Alerts (v3.3)"])
