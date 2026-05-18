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

from app.api import agents, chat_stream, applications, api_keys, workflows, public, projects, tools, skills, data_sources, tool_exec, datasource_test, entity_folders, app_versions, workflow_versions, model_providers, usage, media_providers, memories, triggers, mcp_servers, app_templates, audit, admin_quota, user_quotas, quota_alerts, run_history, approvals, webhook_outbox, heartbeats, conv_cost, admin_billing, slow_queries
from app.core.trigger_worker import trigger_worker_loop
from app.core.trigger_dispatcher import trigger_dispatcher_loop
from app.core.quota_alert_worker import alert_worker_loop
from app.core.resume_worker import resume_worker_loop
from app.core.webhook_outbox import webhook_dispatcher_loop
from app.config import settings
from app.utils.migrate import run_alembic_upgrade
from app.middleware.legacy_bridge import LegacyURLBridge
from staffkm_core.utils import database as _db
from staffkm_core.utils.database import init_db
from staffkm_core.observability import setup_otel, instrument_fastapi
from staffkm_tenant import TenantContextMiddleware

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_otel(service_name="staffkm-agent")
    init_db(settings.DB_URL)
    # v3.7 P4: slow query trace (>SLOW_QUERY_THRESHOLD_MS ms → log + OTel span tag)
    try:
        from app.core.slow_query import install_slow_query_listener
        if _db._engine is not None:
            install_slow_query_listener(_db._engine)
    except Exception as _e:
        log.warning("slow_query_install_failed", error=str(_e))
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
    # v3.3 D2：背景啟動 quota alert worker（每 10 分鐘評估 + 派發）
    alert_task = asyncio.create_task(
        alert_worker_loop(lambda: _db._session_factory, interval_sec=600),
    )
    # v3.5 P2：背景啟動 resume worker（每 30s 掃 approved/rejected approvals 續跑 paused run）
    resume_task = asyncio.create_task(
        resume_worker_loop(lambda: _db._session_factory, interval_sec=30),
    )
    # v3.6 P1：webhook outbox dispatcher（每 30s 派發 pending webhooks，含 backoff retry）
    webhook_task = asyncio.create_task(
        webhook_dispatcher_loop(lambda: _db._session_factory, interval_sec=30),
    )
    log.info("agent_service_ready")
    try:
        yield
    finally:
        # v3.6 P4: graceful shutdown — 等 running workflow 收尾才 cancel worker
        log.info("agent_service_shutting_down")
        try:
            import datetime as _dt
            deadline = _dt.datetime.utcnow() + _dt.timedelta(seconds=30)
            from sqlalchemy import text as _text
            while _dt.datetime.utcnow() < deadline:
                if _db._session_factory is None:
                    break
                async with _db._session_factory() as _s:
                    r = await _s.execute(_text(
                        "SELECT COUNT(*) FROM event_trigger_runs WHERE status='running'"
                    ))
                    running = int(r.scalar_one() or 0)
                if running == 0:
                    log.info("graceful_shutdown_no_inflight")
                    break
                log.info("graceful_shutdown_waiting", running=running)
                await asyncio.sleep(2)
            else:
                log.warning("graceful_shutdown_timeout_30s")
        except Exception as e:
            log.warning("graceful_shutdown_check_failed", error=str(e))
        # 取消所有背景 worker
        for t in (worker_task, dispatcher_task, alert_task, resume_task, webhook_task):
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
instrument_fastapi(app, service_name="staffkm-agent")

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
# v3.6 P3: Idempotency-Key — 放在 LegacyURLBridge 內側，
# 確保 key 用 rewritten path（一致 endpoint），但仍在 TenantContext 外（自己讀 X-Workspace-ID）
from app.middleware.idempotency import IdempotencyMiddleware  # noqa: E402
app.add_middleware(IdempotencyMiddleware)
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
app.include_router(run_history.router,        prefix=f"{_PREFIX}/applications", tags=["Workflow Run History (v3.5)"])
app.include_router(usage.router,             prefix=f"{_PREFIX}/usage",        tags=["Token 用量 + Quota（M3）"])
app.include_router(memories.router,          prefix=f"{_PREFIX}/memories",     tags=["Long-term Memory（M4）"])
app.include_router(triggers.router,          prefix=f"{_PREFIX}/triggers",     tags=["Event Triggers（M4）"])
app.include_router(mcp_servers.router,       prefix=f"{_PREFIX}/mcp",          tags=["MCP Hub（M4）"])
app.include_router(app_templates.router,     prefix=f"{_PREFIX}/app-templates",tags=["Workspace App Templates（Sprint 19.x）"])
app.include_router(audit.router,             prefix=f"{_PREFIX}/admin/audit-logs", tags=["Audit Log (v3.0)"])
app.include_router(user_quotas.router,        prefix=f"{_PREFIX}/user-quotas",      tags=["User Quota (v3.3)"])
app.include_router(quota_alerts.router,       prefix=f"{_PREFIX}/quota-alerts",     tags=["Quota Alerts (v3.3)"])
app.include_router(approvals.router,          prefix=f"{_PREFIX}/approvals",        tags=["Workflow Approvals (v3.5)"])
# v3.7 P1：per-conversation cost attribution
app.include_router(conv_cost.router,          prefix=f"{_PREFIX}/conversations",    tags=["Conversation Cost (v3.7)"])

# ── 公開存取 / pre-auth endpoint（不掛 workspace 前綴）──────────────────
app.include_router(public.router,             prefix="/api/v1/public/applications", tags=["公開存取"])
app.include_router(api_keys.public_router,    prefix="/api/v1/api-keys",            tags=["API Key 驗證"])

# ── 全域唯讀 Registry（workspace-agnostic；任何登入者可讀）─────────────
app.include_router(model_providers.router,   prefix="/api/v1/model-providers", tags=["Model Provider Registry（M3）"])
app.include_router(media_providers.router,   prefix="/api/v1/media-providers", tags=["Media Provider Registry（M4）"])

# ── v3.2 P3：admin 跨 workspace quota 管理（不是 workspace-scoped）─────
app.include_router(admin_quota.router,       prefix="/api/v1/admin", tags=["Admin Quota (v3.2)"])

# ── v3.6 P1：admin webhook outbox（跨 workspace 系統 webhooks 監看 + retry）─
app.include_router(webhook_outbox.router,    prefix="/api/v1/admin/webhook-outbox", tags=["Admin Webhook Outbox (v3.6)"])

# ── v3.6 P2：admin worker heartbeats（background loop 健康觀測）─
app.include_router(heartbeats.router,        prefix="/api/v1/admin/heartbeats", tags=["Admin Heartbeats (v3.6)"])

# ── v3.8 P2：admin per-user billing 報表（跨 workspace 真實用了多少錢）─
app.include_router(admin_billing.router,     prefix="/api/v1/admin/billing", tags=["Admin Billing (v3.8)"])

# ── v3.8 P4：admin slow query plan analyzer（自動捕獲 EXPLAIN ANALYZE）─
app.include_router(slow_queries.router,      prefix="/api/v1/admin/slow-queries", tags=["Admin Slow Queries (v3.8)"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "agent"}
