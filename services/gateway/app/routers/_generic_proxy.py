"""通用 backlog 模組 proxy（RFC-006 新 backlog）— tools / skills / data-sources。

每個模組都走相同的 reverse proxy 模式到 agent service。

v3.1：自動把 caller 傳的 `X-Workspace-ID` header 注入到 target URL，
組成 workspace-scoped path（`/api/v1/workspace/{ws}/{prefix}/...`），
讓 agent 的 LegacyURLBridge 不會被 trigger（default 已翻成 410）。
caller 沒帶 header → 退回 legacy `/api/v1/{prefix}/...`，由 bridge 決定 410 / rewrite。
"""
from fastapi import APIRouter, Request

from app.config import settings
from app.utils.proxy import proxy_request


def make_proxy_router(prefix: str) -> APIRouter:
    """產生 /api/v1/{prefix}/* → agent service 的 proxy router。"""
    router = APIRouter()
    base = settings.AGENT_SERVICE_URL

    def _target(request: Request, suffix: str = "") -> str:
        ws = request.headers.get("X-Workspace-ID")
        if ws:
            base_path = f"/api/v1/workspace/{ws}/{prefix}"
        else:
            # legacy fallback；agent 的 LegacyURLBridge 會處理（410 或 rewrite）
            base_path = f"/api/v1/{prefix}"
        return f"{base}{base_path}{suffix}"

    @router.api_route("", methods=["GET", "POST"])
    @router.api_route("/", methods=["GET", "POST"])
    async def proxy_root(request: Request):
        return await proxy_request(request, _target(request))

    @router.api_route("/{path:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE"])
    async def proxy_path(request: Request, path: str):
        suffix = f"/{path}" if path else ""
        return await proxy_request(request, _target(request, suffix))

    return router


tools_router        = make_proxy_router("tools")
skills_router       = make_proxy_router("skills")
data_sources_router = make_proxy_router("data-sources")
folders_router      = make_proxy_router("folders")
model_providers_router = make_proxy_router("model-providers")
media_providers_router = make_proxy_router("media-providers")
# Sprint 19 orphan endpoint cleanup
usage_router        = make_proxy_router("usage")
triggers_router     = make_proxy_router("triggers")
mcp_router          = make_proxy_router("mcp")
memories_router     = make_proxy_router("memories")
app_templates_router = make_proxy_router("app-templates")
# v3.0：audit log（前端在 /admin/audit-logs）
# 注意：prefix 含斜線，注入後 target 是
#   {base}/api/v1/workspace/{ws}/admin/audit-logs/... — 正常 path concat，沒問題
audit_logs_router = make_proxy_router("admin/audit-logs")
# v3.3 D1/D2：user-level quota + quota alerts
user_quotas_router  = make_proxy_router("user-quotas")
quota_alerts_router = make_proxy_router("quota-alerts")
# v3.5 P2：workflow human-approval
approvals_router    = make_proxy_router("approvals")
# v3.7 P1：per-conversation cost attribution
conversations_router = make_proxy_router("conversations")
# v4.7 G：Stripe billing — workspace-scoped (/billing/me, /checkout, /portal, /invoices, /credits/ledger)
billing_router = make_proxy_router("billing")
# v4.9 I：AI-generated workflow（自然語言 → workflow JSON）
workflow_gen_router = make_proxy_router("workflow-gen")


# v4.7 G：Stripe webhook — public path（不需 JWT；不需 workspace header）
def _make_public_billing_router() -> APIRouter:
    router = APIRouter()
    base = settings.AGENT_SERVICE_URL

    @router.api_route("/{path:path}", methods=["GET", "POST"])
    async def _any(request: Request, path: str):
        suffix = f"/{path}" if path else ""
        return await proxy_request(request, f"{base}/api/v1/public/billing{suffix}")

    return router


public_billing_router = _make_public_billing_router()


# v4.10 J：跨 org public workflow marketplace — 不需 JWT、不需 workspace header
def _make_public_marketplace_router() -> APIRouter:
    router = APIRouter()
    base = settings.AGENT_SERVICE_URL

    @router.api_route("", methods=["GET"])
    @router.api_route("/", methods=["GET"])
    async def _root(request: Request):
        return await proxy_request(request, f"{base}/api/v1/public/marketplace")

    @router.api_route("/{path:path}", methods=["GET", "POST"])
    async def _any(request: Request, path: str):
        suffix = f"/{path}" if path else ""
        return await proxy_request(request, f"{base}/api/v1/public/marketplace{suffix}")

    return router


public_marketplace_router = _make_public_marketplace_router()


# v3.2 P3：admin 跨 workspace quota — 非 workspace-scoped，直接 proxy 到 agent
# /api/v1/admin/quotas/...（agent 那邊用 X-User-Roles 判 admin）
def _make_admin_quotas_router() -> APIRouter:
    router = APIRouter()
    base = settings.AGENT_SERVICE_URL

    @router.api_route("", methods=["GET", "POST", "PUT", "DELETE"])
    @router.api_route("/", methods=["GET", "POST", "PUT", "DELETE"])
    async def _root(request: Request):
        return await proxy_request(request, f"{base}/api/v1/admin/quotas")

    @router.api_route("/{path:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE"])
    async def _any(request: Request, path: str):
        suffix = f"/{path}" if path else ""
        return await proxy_request(request, f"{base}/api/v1/admin/quotas{suffix}")

    return router


admin_quotas_router = _make_admin_quotas_router()


# v3.6 P1：admin webhook outbox — 非 workspace-scoped，跨 ws 系統 webhook 監看
def _make_admin_webhook_outbox_router() -> APIRouter:
    router = APIRouter()
    base = settings.AGENT_SERVICE_URL

    @router.api_route("", methods=["GET", "POST"])
    @router.api_route("/", methods=["GET", "POST"])
    async def _root(request: Request):
        return await proxy_request(request, f"{base}/api/v1/admin/webhook-outbox")

    @router.api_route("/{path:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE"])
    async def _any(request: Request, path: str):
        suffix = f"/{path}" if path else ""
        return await proxy_request(request, f"{base}/api/v1/admin/webhook-outbox{suffix}")

    return router


admin_webhook_outbox_router = _make_admin_webhook_outbox_router()


# v3.6 P2：admin worker heartbeats — 非 workspace-scoped，read-only
def _make_admin_heartbeats_router() -> APIRouter:
    router = APIRouter()
    base = settings.AGENT_SERVICE_URL

    @router.api_route("", methods=["GET"])
    @router.api_route("/", methods=["GET"])
    async def _root(request: Request):
        return await proxy_request(request, f"{base}/api/v1/admin/heartbeats")

    @router.api_route("/{path:path}", methods=["GET"])
    async def _any(request: Request, path: str):
        suffix = f"/{path}" if path else ""
        return await proxy_request(request, f"{base}/api/v1/admin/heartbeats{suffix}")

    return router


admin_heartbeats_router = _make_admin_heartbeats_router()


# v3.8 P2：admin per-user billing — 非 workspace-scoped；包含 /users、/users/{id}、/users.csv
def _make_admin_billing_router() -> APIRouter:
    router = APIRouter()
    base = settings.AGENT_SERVICE_URL

    @router.api_route("", methods=["GET"])
    @router.api_route("/", methods=["GET"])
    async def _root(request: Request):
        return await proxy_request(request, f"{base}/api/v1/admin/billing")

    @router.api_route("/{path:path}", methods=["GET"])
    async def _any(request: Request, path: str):
        suffix = f"/{path}" if path else ""
        return await proxy_request(request, f"{base}/api/v1/admin/billing{suffix}")

    return router


admin_billing_router = _make_admin_billing_router()


# v3.8 P4：admin slow query plan analyzer — 非 workspace-scoped，read-only
def _make_admin_slow_queries_router() -> APIRouter:
    router = APIRouter()
    base = settings.AGENT_SERVICE_URL

    @router.api_route("", methods=["GET"])
    @router.api_route("/", methods=["GET"])
    async def _root(request: Request):
        return await proxy_request(request, f"{base}/api/v1/admin/slow-queries")

    @router.api_route("/{path:path}", methods=["GET"])
    async def _any(request: Request, path: str):
        suffix = f"/{path}" if path else ""
        return await proxy_request(request, f"{base}/api/v1/admin/slow-queries{suffix}")

    return router


admin_slow_queries_router = _make_admin_slow_queries_router()


# v4.0 P3/P4：admin worker backend status — 非 workspace-scoped，read-only
def _make_admin_workers_router() -> APIRouter:
    router = APIRouter()
    base = settings.AGENT_SERVICE_URL

    @router.api_route("", methods=["GET"])
    @router.api_route("/", methods=["GET"])
    async def _root(request: Request):
        return await proxy_request(request, f"{base}/api/v1/admin/workers")

    @router.api_route("/{path:path}", methods=["GET"])
    async def _any(request: Request, path: str):
        suffix = f"/{path}" if path else ""
        return await proxy_request(request, f"{base}/api/v1/admin/workers{suffix}")

    return router


admin_workers_router = _make_admin_workers_router()


# v4.1 A：admin starter-pack — 非 workspace-scoped path（agent 內讀 X-Workspace-ID header）
def _make_admin_starter_pack_router() -> APIRouter:
    router = APIRouter()
    base = settings.AGENT_SERVICE_URL

    @router.api_route("", methods=["GET", "POST"])
    @router.api_route("/", methods=["GET", "POST"])
    async def _root(request: Request):
        return await proxy_request(request, f"{base}/api/v1/admin/starter-pack")

    @router.api_route("/{path:path}", methods=["GET", "POST"])
    async def _any(request: Request, path: str):
        suffix = f"/{path}" if path else ""
        return await proxy_request(request, f"{base}/api/v1/admin/starter-pack{suffix}")

    return router


admin_starter_pack_router = _make_admin_starter_pack_router()


# v4.3 Theme C：admin plugins — 列已 load plugins / reload
def _make_admin_plugins_router() -> APIRouter:
    router = APIRouter()
    base = settings.AGENT_SERVICE_URL

    @router.api_route("", methods=["GET", "POST"])
    @router.api_route("/", methods=["GET", "POST"])
    async def _root(request: Request):
        return await proxy_request(request, f"{base}/api/v1/admin/plugins")

    @router.api_route("/{path:path}", methods=["GET", "POST"])
    async def _any(request: Request, path: str):
        suffix = f"/{path}" if path else ""
        return await proxy_request(request, f"{base}/api/v1/admin/plugins{suffix}")

    return router


admin_plugins_router = _make_admin_plugins_router()


# v5.0 K：admin regions registry — 非 workspace-scoped
def _make_admin_regions_router() -> APIRouter:
    router = APIRouter()
    base = settings.AGENT_SERVICE_URL

    @router.api_route("", methods=["GET", "POST"])
    @router.api_route("/", methods=["GET", "POST"])
    async def _root(request: Request):
        return await proxy_request(request, f"{base}/api/v1/admin/regions")

    @router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def _any(request: Request, path: str):
        suffix = f"/{path}" if path else ""
        return await proxy_request(request, f"{base}/api/v1/admin/regions{suffix}")

    return router


admin_regions_router = _make_admin_regions_router()


# v5.0 K：admin conflicts log — 非 workspace-scoped
def _make_admin_conflicts_router() -> APIRouter:
    router = APIRouter()
    base = settings.AGENT_SERVICE_URL

    @router.api_route("", methods=["GET"])
    @router.api_route("/", methods=["GET"])
    async def _root(request: Request):
        return await proxy_request(request, f"{base}/api/v1/admin/conflicts")

    @router.api_route("/{path:path}", methods=["GET", "POST"])
    async def _any(request: Request, path: str):
        suffix = f"/{path}" if path else ""
        return await proxy_request(request, f"{base}/api/v1/admin/conflicts{suffix}")

    return router


admin_conflicts_router = _make_admin_conflicts_router()


# v5.0 K：admin workspace region binding (PUT /admin/workspaces/{id}/region)
def _make_admin_workspaces_router() -> APIRouter:
    router = APIRouter()
    base = settings.AGENT_SERVICE_URL

    @router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def _any(request: Request, path: str):
        suffix = f"/{path}" if path else ""
        return await proxy_request(request, f"{base}/api/v1/admin/workspaces{suffix}")

    return router


admin_workspaces_router = _make_admin_workspaces_router()
