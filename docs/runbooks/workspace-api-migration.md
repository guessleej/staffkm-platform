# Runbook：把既有 Service 遷移到 Workspace 模式

> RFC-001 Stage 2 之後，每個業務 service（knowledge / agent / chat / integration）需要逐一改造 URL 與 query 走 workspace 隔離。本 runbook 給服務維護者照做。

---

## 適用範圍

- 服務內所有「對 user 公開」的 endpoint
- 該服務有業務資源（knowledge_base / application / chat / 等）

不適用：
- `/health`、`/metrics`
- 純內部呼叫（service-to-service）
- 平台級資源（user / workspace 本身、model_provider）

---

## 6 步遷移流程

### Step 1 — 加 staffkm-tenant 套件

更新 service 的 `Dockerfile`：
```dockerfile
COPY --chown=staffkm:staffkm packages/python/staffkm-tenant/staffkm_tenant ./staffkm_tenant
```

### Step 2 — DB 加 workspace_id 欄位

migration `0001_workspace.sql` 已對所有業務表加了 nullable workspace_id。
本 service 的所有 ORM model 同步加：
```python
workspace_id: Mapped[uuid.UUID | None] = mapped_column(
    UUID(as_uuid=True), ForeignKey("workspace.id", ondelete="CASCADE"),
    nullable=True,   # Stage 2 過渡期 nullable；Stage 3 改 NOT NULL
    index=True,
)
```

### Step 3 — 註冊 TenantContextMiddleware

`app/main.py`：
```python
from staffkm_tenant import TenantContextMiddleware
from staffkm_core.utils.database import _session_factory   # 注意：要用全域 factory

app.add_middleware(
    TenantContextMiddleware,
    session_factory=_session_factory,
    user_id_getter=lambda req: uuid.UUID(req.state.user_id) if req.state.user_id else None,
)
```

### Step 4 — URL 路徑改造

舊：
```
GET  /api/v1/knowledge/bases
POST /api/v1/knowledge/documents/{kb_id}/upload
```

新（注意必須加 `/workspace/{workspace_id}/`）：
```
GET  /api/v1/workspace/{workspace_id}/knowledge/bases
POST /api/v1/workspace/{workspace_id}/knowledge/documents/{kb_id}/upload
```

對應的 router prefix：
```python
app.include_router(
    knowledge_bases.router,
    prefix="/api/v1/workspace/{workspace_id}/knowledge/bases",
    tags=["知識庫"],
)
```

### Step 5 — Query 改用 WorkspaceScopedQuery

舊（**禁止**）：
```python
result = await session.execute(
    select(KnowledgeBase).where(KnowledgeBase.is_public == True)
)
```

新：
```python
from staffkm_tenant import WorkspaceScopedQuery

q = WorkspaceScopedQuery(KnowledgeBase).select().where(
    KnowledgeBase.is_public == True
)
result = await session.execute(q)
```

`WorkspaceScopedQuery` 自動加 `WHERE workspace_id = <current>`，呼叫者跨 workspace 即 403。

### Step 6 — 權限 dependency

需要寫權限的 endpoint：
```python
from staffkm_tenant import require_writer, require_admin, require_owner

@router.delete("/{kb_id}")
async def delete_kb(
    kb_id: UUID,
    ctx = Depends(require_admin),   # 自動 403 若不是 admin/owner
    session: AsyncSession = Depends(get_session),
):
    ...
```

可用的 dependency：

| 名稱 | 允許角色 |
|------|---------|
| `require_member` | 任何成員（owner / admin / editor / viewer） |
| `require_writer` | owner / admin / editor |
| `require_admin`  | owner / admin |
| `require_owner`  | owner |
| `require_role(WorkspaceRole.X, ...)` | 自訂組合 |

### Step 7 — Gateway 路由更新

services/gateway/app/routers/knowledge.py（範例）：
```python
@router.api_route("/{path:path}", methods=["GET", "POST", "PATCH", "DELETE"])
async def proxy_knowledge(request: Request, path: str):
    # 路徑已含 workspace_id，原樣轉發
    return await proxy_request(request, f"{BASE}/api/v1/workspace/{path}")
```

需把 prefix 由 `/api/v1/knowledge` 改為 `/api/v1/workspace`，同時把所有 client 的呼叫對應改寫。

### Step 8 — 寫測試

每個改過的 endpoint 至少 3 個 E2E case：
1. 同 workspace 成員可讀
2. **不同 workspace 成員 → 403**
3. 正確角色可寫、低階角色 → 403

---

## 過渡期相容（v1 endpoint 保留）

為了不打斷既有 client：

```python
# 舊 endpoint 保留 6 個月，加 deprecation header
from fastapi import APIRouter

deprecated_router = APIRouter()

@deprecated_router.get("/api/v1/knowledge/bases", deprecated=True)
async def legacy_list_kbs(...):
    response.headers["Sunset"] = "Wed, 15 Nov 2026 00:00:00 GMT"
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = '</api/v1/workspace/{ws_id}/knowledge/bases>; rel="successor-version"'
    # 自動把舊呼叫導到 default workspace
    request.state.workspace_id = DEFAULT_WORKSPACE_ID
    ...
```

---

## 各服務遷移狀態

| Service | 加套件 | 加 middleware | URL 改 | ScopedQuery | 權限 dep | 測試 |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|
| auth         | n/a    | n/a    | n/a    | n/a    | n/a   | n/a   |
| knowledge    | ⬜     | ⬜     | ⬜     | ⬜     | ⬜    | ⬜    |
| agent        | ⬜     | ⬜     | ⬜     | ⬜     | ⬜    | ⬜    |
| chat         | ⬜     | ⬜     | ⬜     | ⬜     | ⬜    | ⬜    |
| integration  | ⬜     | ⬜     | ⬜     | ⬜     | ⬜    | ⬜    |

每完成一個服務，更新本表並加 issue link。

---

## 驗證 Checklist（合 PR 前）

- [ ] 所有 `select(BusinessModel)` 已替換為 `WorkspaceScopedQuery`
- [ ] 沒有 raw SQL 漏掉 workspace_id
- [ ] E2E 跨 workspace 測試 = 403
- [ ] 舊 client 仍可運作（v1 endpoint deprecated 但活著）
- [ ] OpenAPI spec 更新
- [ ] migration 已在 staging 跑過

---

## 跨 workspace 漏查的稽核 SQL

定期跑（建議 weekly cron）：

```sql
-- 找出所有 business 表中 workspace_id 為 NULL 的列
SELECT 'knowledge_bases' AS t, COUNT(*) FROM knowledge_bases WHERE workspace_id IS NULL
UNION ALL
SELECT 'documents', COUNT(*) FROM documents WHERE workspace_id IS NULL
UNION ALL
SELECT 'applications', COUNT(*) FROM applications WHERE workspace_id IS NULL;
```

正式上線後此查詢應該全為 0。

---

## 反向操作（Rollback）

若遷移後發現問題，可回退單一 service：
1. revert 該 service 的 PR
2. 舊 v1 endpoint 仍活著（沒砍）
3. DB schema 不需要 rollback（只是欄位 nullable）

---

## 相關文件

- [RFC-001: Multi-tenant 設計](../rfc/RFC-001-multi-tenant.md)
- [packages/python/staffkm-tenant/README.md](../../packages/python/staffkm-tenant/README.md)
- [Migration 0001_workspace.sql](../../packages/sql/migrations/0001_workspace.sql)
