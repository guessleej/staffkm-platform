"""Agent Service — 多場景行政 AI 代理人服務（RFC-001 Stage 2: workspace-scoped）"""
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import agents, chat_stream, applications, api_keys, workflows, public, projects, tools, skills, data_sources, tool_exec, datasource_test, entity_folders, app_versions, workflow_versions, model_providers
from app.bootstrap_ddl import run_bootstrap_ddl
from app.config import settings
from app.middleware.legacy_bridge import LegacyURLBridge
from staffkm_core.utils import database as _db
from staffkm_core.utils.database import init_db
from staffkm_tenant import TenantContextMiddleware

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(settings.DB_URL)
    await run_bootstrap_ddl()
    log.info("agent_service_ready")
    yield


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

# ── Middleware（starlette 規則：後加 = 外層 = 先跑）──────────────────
# 期望執行順序（request 進來時）：
#   LegacyURLBridge → GatewayHeaders → TenantContext → endpoint
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
app.include_router(model_providers.router,   prefix=f"{_PREFIX}/model-providers", tags=["Model Provider Registry（M3）"])

# ── 公開存取 / pre-auth endpoint（不掛 workspace 前綴）──────────────────
app.include_router(public.router,             prefix="/api/v1/public/applications", tags=["公開存取"])
app.include_router(api_keys.public_router,    prefix="/api/v1/api-keys",            tags=["API Key 驗證"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "agent"}
