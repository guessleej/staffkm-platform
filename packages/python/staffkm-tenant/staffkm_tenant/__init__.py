"""staffkm-tenant — multi-tenant workspace + RBAC/ABAC.

Public API:
    Workspace, WorkspaceMember              — ORM models
    WorkspaceRole                            — Enum: owner / admin / editor / viewer
    TenantContext, get_tenant_context        — request-scoped context
    TenantContextMiddleware                  — FastAPI middleware
    require_role, require_member             — dependency / decorator
    WorkspaceScopedQuery                     — auto-filter ORM queries by workspace
    WorkspacePermissionError                 — exception
"""
from staffkm_tenant.models import Workspace, WorkspaceMember, WorkspaceRole
from staffkm_tenant.context import TenantContext, get_tenant_context
from staffkm_tenant.middleware import TenantContextMiddleware
from staffkm_tenant.permissions import (
    require_role,
    require_member,
    WorkspacePermissionError,
)
from staffkm_tenant.scoped_query import WorkspaceScopedQuery

__all__ = [
    "Workspace",
    "WorkspaceMember",
    "WorkspaceRole",
    "TenantContext",
    "get_tenant_context",
    "TenantContextMiddleware",
    "require_role",
    "require_member",
    "WorkspacePermissionError",
    "WorkspaceScopedQuery",
]
