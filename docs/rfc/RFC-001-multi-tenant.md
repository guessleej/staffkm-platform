# RFC-001: Multi-tenant Workspace 設計

| 欄位 | 內容 |
|------|------|
| 編號 | RFC-001 |
| 提案者 | @architect |
| 狀態 | Draft |
| 建立日期 | 2026-05-15 |
| Reviewers | @lead-be @lead-fe @pmp |

---

## 1. 摘要

引入 **workspace（工作區）** 作為所有資源（user / kb / app / model / folder）的歸屬單位。一個 user 可加入多個 workspace、扮演不同角色。所有 API 在 URL 上帶 `workspace_id`，DB row level 強制隔離。

## 2. 動機

目前 staffKM 沒有租戶概念，所有資源全域可見。MaxKB 已實作 workspace 並把它當核心抽象。要支援以下情境必須引入：
- 不同部門 / 子公司資料隔離（人事、法務、IT 各自 workspace）
- SaaS 化（每客戶 = 1 workspace）
- 一個帳號跨多個專案（顧問常見）
- 細粒度權限（部門主管只能管自己 workspace）

## 3. 目標與非目標

**目標**
- [ ] G1：所有業務資源（kb / app / model / folder / chat / api_key）以 workspace 隔離
- [ ] G2：一個 user 可加入 N 個 workspace，每個 workspace 可有不同 role
- [ ] G3：URL 結構帶 workspace_id：`/api/v1/workspace/{ws_id}/...`
- [ ] G4：DB 層 row-level security，誤查跨 workspace 資料會直接 raise
- [ ] G5：Admin 能跨 workspace（system role）

**非目標**
- N1：不做 schema-per-tenant（用 row-level 即可，運維簡單）
- N2：不支援跨 workspace 共享資源（Phase 2 再說）
- N3：不做 workspace 計費（Phase 5）

## 4. 提案設計

### 4.1 資料模型

```
┌──────────────┐         ┌────────────────────┐         ┌──────────┐
│    user      │  N : N  │  workspace_member  │  N : 1  │workspace │
│  (全域唯一)   │─────────│  (role: owner/    │─────────│          │
│              │         │   admin/editor/    │         │          │
│              │         │   viewer)          │         │          │
└──────────────┘         └────────────────────┘         └──────────┘
                                                              │
                                                              │ 1 : N
                                                              ▼
                                  ┌──────────────────────────────────┐
                                  │  knowledge / application / model │
                                  │  / folder / api_key / chat       │
                                  │      （皆有 workspace_id FK）     │
                                  └──────────────────────────────────┘
```

### 4.2 核心 Schema

```sql
CREATE TABLE workspace (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(128) NOT NULL,
    slug        VARCHAR(64)  NOT NULL UNIQUE,  -- URL-friendly
    plan        VARCHAR(32)  NOT NULL DEFAULT 'free',
    quota_meta  JSONB        NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ
);

CREATE TABLE workspace_member (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id  UUID NOT NULL REFERENCES workspace(id) ON DELETE CASCADE,
    user_id       UUID NOT NULL REFERENCES "user"(id)   ON DELETE CASCADE,
    role          VARCHAR(32) NOT NULL,    -- owner / admin / editor / viewer
    invited_at    TIMESTAMPTZ DEFAULT now(),
    joined_at     TIMESTAMPTZ,
    UNIQUE (workspace_id, user_id)
);

-- 既有資源表全部加 workspace_id
ALTER TABLE knowledge_bases  ADD COLUMN workspace_id UUID REFERENCES workspace(id);
ALTER TABLE applications     ADD COLUMN workspace_id UUID REFERENCES workspace(id);
ALTER TABLE ai_models        ADD COLUMN workspace_id UUID REFERENCES workspace(id);
-- ... 共 8 張表

-- 強制 index 加速 row-level filter
CREATE INDEX idx_kb_workspace ON knowledge_bases(workspace_id);
-- ... 同樣處理
```

### 4.3 RBAC × ABAC 權限模型

**Role**（粗粒度，固定 4 級）：

| Role | 權限 |
|------|------|
| `owner` | 全部 + 刪除 workspace + 計費 |
| `admin` | 管理 member + 全部資源 CRUD |
| `editor` | 建立 / 編輯資源、不能刪 workspace、不能管 member |
| `viewer` | 唯讀 |

**ABAC 屬性**（細粒度，補充用）：

```python
# 例：folder 的擁有者可在該 folder 內 CRUD，外人 viewer
@require_attribute(folder_owner=True)
def update_folder(...): ...

# 例：模型的可見性
class AIModel:
    visibility: Literal['private', 'workspace', 'public']
    # private = 只有建立者
    # workspace = workspace 成員可用
    # public = 跨 workspace（admin 才能設）
```

### 4.4 API 路徑慣例

```
舊：GET /api/v1/knowledge/bases
新：GET /api/v1/workspace/{ws_id}/knowledge/bases

舊：POST /api/v1/applications
新：POST /api/v1/workspace/{ws_id}/applications
```

### 4.5 中介軟體

```python
# core/middleware/tenant.py
class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        ws_id = request.path_params.get("workspace_id")
        if ws_id:
            # 驗證 user 是該 workspace member
            member = await verify_membership(request.user, ws_id)
            if not member:
                return JSONResponse({"error": "forbidden"}, status_code=403)
            # 注入 context（後續 query 自動帶 filter）
            request.state.workspace_id = ws_id
            request.state.role = member.role
        return await call_next(request)
```

### 4.6 ORM Query 護欄

```python
# core/db/scoped_query.py
class WorkspaceScopedQuery:
    """所有業務 model query 必須走這個 helper，自動加 workspace filter。"""
    @staticmethod
    async def all(model, request):
        ws_id = request.state.workspace_id
        return await session.execute(
            select(model).where(model.workspace_id == ws_id)
        )
```

> 配合 lint rule 禁止業務 service 直接寫 raw `select(KnowledgeBase)`，必須用 helper。

## 5. 替代方案

| 方案 | 優點 | 缺點 | 為何不選 |
|------|------|------|----------|
| Schema-per-tenant | 物理隔離強 | migration 痛苦、connection pool 爆 | 維運成本太高 |
| DB-per-tenant | 最強隔離 | 資源浪費、跨庫查詢困難 | 不適合單一 product |
| 不做 workspace（沿用全域）| 最快 | 無法滿足採用情境 | 違反 G1-G3 |
| **Row-level + middleware（本提案）** | **平衡、業界主流** | 漏寫 filter 是風險 | **採用** + lint 保險 |

## 6. 風險與緩解

| 風險 | 機率 | 衝擊 | 緩解 |
|------|------|------|------|
| 開發者忘記加 workspace filter → 跨 tenant 資料外洩 | 高 | 致命 | lint rule + code review checklist + integration test 強制驗證 |
| Migration 既有資料無 workspace_id | 確定 | 中 | 建立 `default` workspace 收容所有舊資料 |
| URL 變動讓 v1 client 全壞 | 高 | 高 | v1 endpoint 保留 6 個月並轉發到 default workspace |
| Owner 離職 workspace 變孤兒 | 中 | 中 | 強制 ≥ 2 owner、admin 可申請接管 |

## 7. 影響範圍

- **DB**：新增 2 表 + 8 張既有表加 column；migration 約 1 天
- **API**：URL 全改 → breaking change → 走 v1 → v2 兩條 route 6 個月並行
- **效能**：每 query 多一個 indexed where → 影響 < 5%
- **資安**：強化（隔離），但需要 lint + test 把關

## 8. 推出計畫

- [ ] **Stage 1**（W1）：建立 schema、middleware、helper；feature flag `WORKSPACE_ENABLED=false`，舊 API 不變
- [ ] **Stage 2**（W2）：把所有舊資料遷至 `default` workspace，啟動雙寫
- [ ] **Stage 3**（W2）：新 API endpoint `/workspace/{ws_id}/...` 上線
- [ ] **Stage 4**（W3）：前端切換到新 endpoint
- [ ] **Stage 5**（W3）：M1 通過後 default-on
- [ ] **Stage 6**（+6 月）：v1 endpoint 移除

回滾：feature flag 一秒切回 v1，data 已雙寫不會丟。

## 9. 量測指標

- 上線 30 天：跨 workspace 漏查 = 0（透過自動化稽核 SQL）
- API latency 變化 < 5%
- 平均每 user 加入 workspace 數（產品健康度指標）

## 10. 開放問題

- [ ] Q1：workspace slug 改名是否允許？（影響 URL 持久性）@product to decide by W1 Wed
- [ ] Q2：邀請流程要不要 email？還是純邀請連結？@ux to design by W1 Fri
- [ ] Q3：跨 workspace 共享 model 怎麼定價？@pmp to spec by Phase 3

## 11. 參考資料

- [Multi-tenant SaaS patterns (AWS)](https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/multi-tenant.html)
- [PostgreSQL Row Level Security](https://www.postgresql.org/docs/16/ddl-rowsecurity.html)
- MaxKB workspace_id 用法（從 docker exec 分析得到）
- 相關 RFC：RFC-002（Workflow Engine v2 也需要 workspace 隔離）
