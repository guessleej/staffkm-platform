# staffkm-tenant

> Multi-tenant workspace + RBAC/ABAC 共用套件（RFC-001 Stage 1）

## 概念

```
User ── N:N ──► WorkspaceMember (role) ──► Workspace ──► 資源 (KB / App / Model …)
```

每個 request 都帶 `workspace_id`，middleware 驗證 user 是該 workspace 的 active member 後注入 `TenantContext`，所有 ORM query 走 `WorkspaceScopedQuery` 自動過濾。

## 角色

| Role | manage workspace | manage members | write | read |
|------|:---:|:---:|:---:|:---:|
| owner  | ✅ | ✅ | ✅ | ✅ |
| admin  |  | ✅ | ✅ | ✅ |
| editor |  |  | ✅ | ✅ |
| viewer |  |  |  | ✅ |

## 用法

### 1. 註冊 middleware

```python
from staffkm_tenant import TenantContextMiddleware

app.add_middleware(
    TenantContextMiddleware,
    session_factory=session_factory,
    user_id_getter=lambda req: req.state.user_id,  # 從你的 auth middleware 拿
)
```

### 2. 在 endpoint 用 dependency 控制權限

```python
from fastapi import Depends
from staffkm_tenant import require_role, WorkspaceRole

@router.delete("/api/v1/workspace/{workspace_id}/knowledge/{kb_id}")
async def delete_kb(
    kb_id: UUID,
    ctx = Depends(require_role(WorkspaceRole.OWNER, WorkspaceRole.ADMIN)),
):
    ...
```

### 3. 業務 query 走 ScopedQuery

```python
from staffkm_tenant import WorkspaceScopedQuery
from app.models import KnowledgeBase

# ✅ 安全：自動帶 workspace_id 過濾
q = WorkspaceScopedQuery(KnowledgeBase).select()
result = await session.execute(q)
```

## URL 慣例

```
/api/v1/workspace/{workspace_id}/knowledge/...
/api/v1/workspace/{workspace_id}/applications/...
```

middleware 用 regex `/workspace/([uuid])/` 偵測，**沒中** workspace pattern 的 endpoint（如 `/auth/login`、`/workspaces`）會直接 pass。

## 測試

```bash
cd packages/python/staffkm-tenant
uv run pytest
```

## 對應 RFC

[RFC-001: Multi-tenant Workspace 設計](../../../docs/rfc/RFC-001-multi-tenant.md)
