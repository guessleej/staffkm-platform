"""權限檢查 — FastAPI dependency 與 decorator。"""
from fastapi import Depends, HTTPException, status

from staffkm_tenant.context import TenantContext, get_tenant_context
from staffkm_tenant.models import WorkspaceRole


class WorkspacePermissionError(HTTPException):
    """權限不足。"""
    def __init__(self, detail: str = "permission denied"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


# ─── Dependency-style：FastAPI 的 Depends() ─────────────────────────

def require_member(ctx: TenantContext = Depends(get_tenant_context)) -> TenantContext:
    """任何 workspace 成員都可（最寬鬆）。"""
    return ctx


def require_role(*allowed: WorkspaceRole):
    """要求 role 在 allowed 之中，否則 403。

    用法：
        @router.delete("/...")
        async def delete_kb(
            ctx: TenantContext = Depends(require_role(WorkspaceRole.OWNER, WorkspaceRole.ADMIN))
        ): ...
    """
    def _check(ctx: TenantContext = Depends(get_tenant_context)) -> TenantContext:
        if ctx.is_system or ctx.role in allowed:
            return ctx
        raise WorkspacePermissionError(
            f"required role: {', '.join(r.value for r in allowed)}; got {ctx.role.value}"
        )
    return _check


# 常用組合
require_writer = require_role(WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.EDITOR)
require_admin  = require_role(WorkspaceRole.OWNER, WorkspaceRole.ADMIN)
require_owner  = require_role(WorkspaceRole.OWNER)
