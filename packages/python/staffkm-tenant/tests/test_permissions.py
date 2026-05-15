"""Unit tests — RBAC role 邏輯與 permission helpers。"""
import uuid
import pytest
from fastapi import HTTPException

from staffkm_tenant.context import TenantContext, set_tenant_context, clear_tenant_context
from staffkm_tenant.models import WorkspaceRole
from staffkm_tenant.permissions import (
    require_role, require_writer, require_admin, require_owner,
    WorkspacePermissionError,
)


@pytest.fixture(autouse=True)
def _isolate_context():
    yield
    clear_tenant_context()


def _ctx(role: WorkspaceRole, system: bool = False) -> TenantContext:
    return TenantContext(
        workspace_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role=role,
        is_system=system,
    )


# ─── WorkspaceRole 屬性 ─────────────────────────────────────────────
class TestWorkspaceRole:
    def test_owner_can_do_all(self):
        assert WorkspaceRole.OWNER.can_manage_workspace
        assert WorkspaceRole.OWNER.can_manage_members
        assert WorkspaceRole.OWNER.can_write
        assert WorkspaceRole.OWNER.can_read

    def test_admin_cannot_manage_workspace_but_can_manage_members(self):
        assert not WorkspaceRole.ADMIN.can_manage_workspace
        assert WorkspaceRole.ADMIN.can_manage_members
        assert WorkspaceRole.ADMIN.can_write

    def test_editor_can_write_but_not_manage_members(self):
        assert not WorkspaceRole.EDITOR.can_manage_members
        assert WorkspaceRole.EDITOR.can_write

    def test_viewer_can_only_read(self):
        assert not WorkspaceRole.VIEWER.can_write
        assert WorkspaceRole.VIEWER.can_read


# ─── TenantContext computed properties ─────────────────────────────
class TestTenantContext:
    def test_system_can_do_anything(self):
        ctx = _ctx(WorkspaceRole.VIEWER, system=True)
        assert ctx.can_write
        assert ctx.can_manage_members
        assert ctx.can_manage_workspace

    def test_viewer_cannot_write(self):
        ctx = _ctx(WorkspaceRole.VIEWER)
        assert not ctx.can_write


# ─── require_role decorator ────────────────────────────────────────
class TestRequireRole:
    def test_allowed_role_passes(self):
        ctx = _ctx(WorkspaceRole.ADMIN)
        set_tenant_context(ctx)
        check = require_role(WorkspaceRole.OWNER, WorkspaceRole.ADMIN)
        # 直接呼叫底層函式（不走 Depends）
        result = check(ctx)
        assert result is ctx

    def test_disallowed_role_raises(self):
        ctx = _ctx(WorkspaceRole.VIEWER)
        check = require_role(WorkspaceRole.OWNER)
        with pytest.raises(WorkspacePermissionError) as exc:
            check(ctx)
        assert exc.value.status_code == 403

    def test_system_user_bypasses(self):
        ctx = _ctx(WorkspaceRole.VIEWER, system=True)
        check = require_role(WorkspaceRole.OWNER)
        assert check(ctx) is ctx

    def test_require_writer_includes_editor(self):
        ctx = _ctx(WorkspaceRole.EDITOR)
        assert require_writer(ctx) is ctx

    def test_require_writer_excludes_viewer(self):
        ctx = _ctx(WorkspaceRole.VIEWER)
        with pytest.raises(WorkspacePermissionError):
            require_writer(ctx)


# ─── ContextVar isolation ──────────────────────────────────────────
class TestContextVar:
    def test_unset_raises(self):
        from staffkm_tenant.context import get_tenant_context
        clear_tenant_context()
        with pytest.raises(RuntimeError, match="TenantContext 未設定"):
            get_tenant_context()

    def test_set_then_get(self):
        from staffkm_tenant.context import get_tenant_context
        ctx = _ctx(WorkspaceRole.OWNER)
        set_tenant_context(ctx)
        assert get_tenant_context() is ctx
