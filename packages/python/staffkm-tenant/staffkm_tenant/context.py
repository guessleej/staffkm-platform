"""請求作用域的 tenant context — 由 middleware 注入、由 dependency / scoped query 讀取。"""
import uuid
from contextvars import ContextVar
from dataclasses import dataclass

from staffkm_tenant.models import WorkspaceRole


@dataclass(frozen=True)
class TenantContext:
    """單一請求的多租戶上下文。"""
    workspace_id: uuid.UUID
    user_id:      uuid.UUID
    role:         WorkspaceRole
    is_system:    bool = False  # superadmin 可跨 workspace

    @property
    def can_write(self) -> bool:
        return self.is_system or self.role.can_write

    @property
    def can_manage_members(self) -> bool:
        return self.is_system or self.role.can_manage_members

    @property
    def can_manage_workspace(self) -> bool:
        return self.is_system or self.role.can_manage_workspace


# ContextVar — async-safe，每個 request 一份
_current_tenant: ContextVar[TenantContext | None] = ContextVar(
    "current_tenant", default=None
)


def set_tenant_context(ctx: TenantContext) -> None:
    """由 middleware 呼叫，在請求生命週期內注入 context。"""
    _current_tenant.set(ctx)


def get_tenant_context() -> TenantContext:
    """於 service / repository 取得當前 tenant context。
    若 context 未設定（例如 background task 沒走 middleware），會 raise。"""
    ctx = _current_tenant.get()
    if ctx is None:
        raise RuntimeError(
            "TenantContext 未設定。確認 (1) request 經過 TenantContextMiddleware；"
            "或 (2) 背景任務 / Celery worker 手動呼叫 set_tenant_context()。"
        )
    return ctx


def clear_tenant_context() -> None:
    _current_tenant.set(None)
