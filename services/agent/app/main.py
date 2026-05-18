"""Agent Service — 多場景行政 AI 代理人服務（RFC-001 Stage 2: workspace-scoped）"""
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.usage import QuotaExceeded

import asyncio

from app.api import agents, chat_stream, applications, api_keys, workflows, public, projects, tools, skills, data_sources, tool_exec, datasource_test, entity_folders, app_versions, workflow_versions, model_providers, usage, media_providers, memories, triggers, mcp_servers, app_templates, audit, admin_quota
from app.core.trigger_worker import trigger_worker_loop
from app.core.trigger_dispatcher import trigger_dispatcher_loop
from app.bootstrap_ddl import run_bootstrap_ddl
from app.config import settings
from app.utils.migrate import run_alembic_upgrade
from app.middleware.legacy_bridge import LegacyURLBridge
from staffkm_core.utils import database as _db
from staffkm_core.utils.database import init_db
from staffkm_tenant import TenantContextMiddleware

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(settings.DB_URL)
    await run_bootstrap_ddl()
    await run_alembic_upgrade()
    # v3.2 P1：seed 已知 model 的 USD/1k token 定價（idempotent，只補 NULL）
    from app.core.pricing_seed import seed_model_pricing
    await seed_model_pricing(_db._session_factory)
    # M4：背景啟動 trigger worker（每 60s 掃 due triggers 寫 queued run）
    worker_task = asyncio.create_task(
        trigger_worker_loop(lambda: _db._session_factory, interval_sec=60),
    )
    # v2.1 12-4：背景啟動 dispatcher（每 10s 從 queued runs 真實執行 workflow）
    dispatcher_task = asyncio.create_task(
        trigger_dispatcher_loop(lambda: _db._session_factory, interval_sec=10),
    )
    log.info("agent_service_ready")
    try:
        yield
    finally:
        for t in (worker_task, dispatcher_task):
            t.cancel()
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass


class GatewayHeadersMiddleware(BaseHTTPMiddleware):
    """從 Gateway 注入的 X-User-ID 標頭恢復 request.state（供 tenant middleware 取用）。"""
    async def dispatch(self, request: Request, call_next):
        request.state.user_id = request.headers.get("X-User-ID") or None
        request.state.roles   = [r for r in request.headers.get("X-User-Roles", "").split(",") if r]
        return await call_next(request)


def _user_id_from_request(req: Request) -> uuid.UUID | None:
    raw = getattr(req.state, "user_id", None) or req.headers.get("X-User-ID")
    if not raw:
        return None
    try:
        return uuid.UUID(raw)
    except (TypeError, ValueError):
        return None


app = FastAPI(
    title="StaffKM Agent Service",
    description="多場景行政 AI 代理人服務（v2 workspace-scoped）",
    version="2.0.0",
    lifespan=lifespan,
)

# ── Exception handlers ───────────────────────────────────────────────
@app.exception_handler(QuotaExceeded)
async def _quota_exceeded_handler(request: Request, exc: QuotaExceeded):
    return JSONResponse(
        status_code=429,
        content={"error": "quota_exceeded", "detail": str(exc)},
        headers={"Retry-After": "86400"},  # 1 day
    )


# ── Middleware（starlette 規則：後加 = 外層 = 先跑）──────────────────
# 期望執行順序（request 進來時）：
#   LegacyURLBridge → GatewayHeaders → TenantContext → endpoint
# Prometheus /metrics — v2.2
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(
    TenantContextMiddleware,
    session_factory=lambda: _db._session_factory,
    user_id_getter=_user_id_from_request,
)
app.add_middleware(GatewayHeadersMiddleware)
app.add_middleware(LegacyURLBridge)

# ── Routes（v2：workspace-scoped）─────────────────────────────────────
_PREFIX = "/api/v1/workspace/{workspace_id}"

app.include_router(agents.router,        prefix=f"{_PREFIX}/agents",       tags=["代理人管理"])
app.include_router(chat_stream.router,   prefix=f"{_PREFIX}/agents",       tags=["串流對話"])
app.include_router(applications.router,  prefix=f"{_PREFIX}/applications", tags=["Application Builder"])
app.include_router(workflows.router,     prefix=f"{_PREFIX}/applications", tags=["Workflow 引擎"])
app.include_router(api_keys.router,      prefix=f"{_PREFIX}/api-keys",     tags=["API Key 管理"])
app.include_router(projects.router,      prefix=f"{_PREFIX}/projects",     tags=["Project（RFC-006）"])
app.include_router(tools.router,         prefix=f"{_PREFIX}/tools",        tags=["Tool（新 backlog）"])
app.include_router(tool_exec.router,     prefix=f"{_PREFIX}/tools",        tags=["Tool 執行（D-1）"])
app.include_router(skills.router,        prefix=f"{_PREFIX}/skills",       tags=["Skill（新 backlog）"])
app.include_router(data_sources.router,    prefix=f"{_PREFIX}/data-sources", tags=["Data Source（新 backlog）"])
app.include_router(datasource_test.router, prefix=f"{_PREFIX}/data-sources", tags=["Data Source 連線測試（D-3）"])
app.include_router(entity_folders.router,  prefix=f"{_PREFIX}/folders",      tags=["Entity Folders（D-5）"])
app.include_router(app_versions.router,      prefix=f"{_PREFIX}/applications", tags=["Application 版本控制（D-7）"])
app.include_router(workflow_versions.router, prefix=f"{_PREFIX}/applications", tags=["Workflow 版本控制（M2）"])
app.include_router(usage.router,             prefix=f"{_PREFIX}/usage",        tags=["Token 用量 + Quota（M3）"])
app.include_router(memories.router,          prefix=f"{_PREFIX}/memories",     tags=["Long-term Memory（M4）"])
app.include_router(triggers.router,          prefix=f"{_PREFIX}/triggers",     tags=["Event Triggers（M4）"])
app.include_router(mcp_servers.router,       prefix=f"{_PREFIX}/mcp",          tags=["MCP Hub（M4）"])
app.include_router(app_templates.router,     prefix=f"{_PREFIX}/app-templates",tags=["Workspace App Templates（Sprint 19.x）"])
app.include_router(audit.router,             prefix=f"{_PREFIX}/admin/audit-logs", tags=["Audit Log (v3.0)"])

# ── 公開存取 / pre-auth endpoint（不掛 workspace 前綴）──────────────────
app.include_router(public.router,             prefix="/api/v1/public/applications", tags=["公開存取"])
app.include_router(api_keys.public_router,    prefix="/api/v1/api-keys",            tags=["API Key 驗證"])

# ── 全域唯讀 Registry（workspace-agnostic；任何登入者可讀）─────────────
app.include_router(model_providers.router,   prefix="/api/v1/model-providers", tags=["Model Provider Registry（M3）"])
app.include_router(media_providers.router,   prefix="/api/v1/media-providers", tags=["Media Provider Registry（M4）"])

# ── v3.2 P3：admin 跨 workspace quota 管理（不是 workspace-scoped）─────
app.include_router(admin_quota.router,       prefix="/api/v1/admin", tags=["Admin Quota (v3.2)"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "agent"}
