# RFC-003: Monorepo 結構重組

| 欄位 | 內容 |
|------|------|
| 編號 | RFC-003 |
| 提案者 | @architect |
| 狀態 | Draft |
| 建立日期 | 2026-05-15 |
| Reviewers | @lead-be @lead-fe @devops @pmp |

---

## 1. 摘要

把目前**散亂的 monorepo** 重組為 **pnpm workspace + uv workspace** 雙語管理的標準結構。新增 `apps/`、`packages/`、`tools/`、`infra/` 四個頂層目錄；前端從 `ui/` 升級為 Nuxt 3（接 RFC-004）；後端 services 加入共享 `packages/python/` 取代現有 `core/`。

## 2. 動機

目前結構問題：
- `core/` 在 root，每個 service 用 relative import，**容易壞**
- `ui/` 是 Vite 純 Vue，缺 SSR / file-based routing
- 沒有 shared TypeScript types（前後端 schema 各寫一份）
- `infrastructure/` 與 `services/` 同層，分類不清
- 沒有 `tools/`（CLI、scripts、migration）放的位置
- pnpm/uv 沒設定 workspace，依賴管理零散

## 3. 目標與非目標

**目標**
- [ ] G1：清晰的 4 層目錄：apps / packages / tools / infra
- [ ] G2：前端 / 後端共享 type（OpenAPI codegen）
- [ ] G3：pnpm workspace（TS）+ uv workspace（Python）統一依賴
- [ ] G4：每個 sub-project 可獨立 build / test / lint
- [ ] G5：CI matrix 自動偵測哪些 package 改動，只跑相關 job

**非目標**
- N1：不引入 Nx / Turborepo（先用 pnpm workspace + Makefile 夠用）
- N2：不拆 git submodule（重組是 in-place 改名 + 移動）

## 4. 提案設計

### 4.1 新目錄結構

```
staffKM/
├── apps/                          # 可獨立部署的應用
│   ├── web/                       # ← 原 ui/，升級為 Nuxt 3
│   ├── docs/                      # ← 新增：Docusaurus 文件站
│   ├── marketing/                 # ← 新增：landing page (Astro)
│   └── admin-cli/                 # ← 新增：CLI 工具
│
├── services/                      # 後端微服務（沿用，但統一規範）
│   ├── gateway/
│   ├── auth/
│   ├── knowledge/
│   ├── agent/
│   ├── chat/
│   └── integration/
│
├── packages/                      # 共享套件
│   ├── python/
│   │   ├── staffkm-core/          # ← 原 core/，重新命名
│   │   ├── staffkm-models/        # 共享 SQLAlchemy models
│   │   ├── staffkm-workflow/      # workflow engine v2 抽出
│   │   ├── staffkm-providers/     # model providers 抽出
│   │   └── staffkm-tenant/        # 多租戶 middleware
│   ├── ts/
│   │   ├── ui-kit/                # 共享 Vue 元件庫
│   │   ├── api-types/             # OpenAPI codegen 產物
│   │   ├── sdk/                   # JS/TS SDK（自動產生）
│   │   └── design-tokens/         # 設計系統 token
│   └── sql/
│       └── migrations/            # Alembic + 共享 DDL
│
├── tools/                         # 開發 / 部署工具
│   ├── codegen/                   # OpenAPI → TS types
│   ├── scripts/                   # 部署、備份、demo seed
│   ├── docker/                    # 共享 Dockerfile 片段
│   └── e2e/                       # Playwright E2E suite
│
├── infra/                         # 基礎設施即程式碼
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   ├── helm/                      # K8s Helm charts (Phase 5)
│   ├── terraform/                 # 雲端 IaC（將來）
│   ├── postgres/                  # init.sql、postgresql.conf
│   ├── nginx/                     # nginx 設定
│   └── monitoring/                # Prometheus / Grafana 設定
│
├── docs/                          # 專案治理文件（已有）
│   ├── rfc/
│   ├── governance/
│   ├── adr/
│   └── runbooks/
│
├── .github/                       # GitHub 設定
│   ├── ISSUE_TEMPLATE/
│   ├── workflows/                 # CI/CD
│   └── PULL_REQUEST_TEMPLATE.md
│
├── pnpm-workspace.yaml            # ← 新
├── pyproject.toml                 # ← 新（uv workspace root）
├── Makefile                       # 統一指令入口
├── README.md
└── CHANGELOG.md
```

### 4.2 Workspace 設定

**`pnpm-workspace.yaml`**
```yaml
packages:
  - 'apps/*'
  - 'packages/ts/*'
  - 'tools/codegen'
  - 'tools/e2e'
```

**`pyproject.toml`（root）**
```toml
[tool.uv.workspace]
members = [
    "services/*",
    "packages/python/*",
    "apps/admin-cli",
]

[tool.uv.sources]
staffkm-core      = { workspace = true }
staffkm-models    = { workspace = true }
staffkm-workflow  = { workspace = true }
staffkm-providers = { workspace = true }
staffkm-tenant    = { workspace = true }
```

### 4.3 共享套件依賴範例

```toml
# services/knowledge/pyproject.toml
[project]
name = "staffkm-knowledge"
dependencies = [
    "staffkm-core",       # ← workspace 內套件
    "staffkm-models",
    "staffkm-tenant",
    "fastapi>=0.115",
    "sqlalchemy>=2.0",
]
```

### 4.4 OpenAPI 型別共享流程

```
services/knowledge (FastAPI)
        │
        │ /openapi.json
        ▼
tools/codegen (openapi-typescript)
        │
        │ generate .d.ts
        ▼
packages/ts/api-types
        │
        │ pnpm 連結
        ▼
apps/web → import type { KnowledgeBase } from '@staffkm/api-types'
```

`make codegen` 一次更新所有 TS types。CI 強制檢查 `git diff` 為空（沒人手改 types）。

### 4.5 Makefile（統一指令）

```makefile
# 開發
dev:           ## 啟動完整開發環境
	docker compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up -d

dev-web:       ## 只啟前端（連 staging API）
	cd apps/web && pnpm dev

# 程式碼產生
codegen:       ## 從 OpenAPI 產生 TS types
	uv run python tools/codegen/openapi_export.py
	pnpm --filter @staffkm/api-types build

# 測試
test:          ## 跑所有測試
	uv run pytest
	pnpm -r test
	pnpm --filter e2e test

test-be:       ## 後端測試
test-fe:       ## 前端測試
test-e2e:      ## Playwright E2E

# 建置
build:         ## 建置所有 image
	docker compose -f infra/docker-compose.yml build --parallel

# 品質
lint:          ## lint 全部
	uv run ruff check .
	uv run mypy .
	pnpm -r lint

format:        ## format 全部
	uv run ruff format .
	pnpm -r format

# 治理
rfc-new:       ## 建立新 RFC
	@scripts/new-rfc.sh

migrate:       ## DB migration
	uv run alembic upgrade head
```

### 4.6 遷移腳本

```bash
# tools/scripts/migrate-to-v2-structure.sh
git mv ui apps/web
git mv core packages/python/staffkm-core
git mv infrastructure infra
mkdir -p apps/docs apps/marketing apps/admin-cli
mkdir -p packages/python/{staffkm-models,staffkm-workflow,staffkm-providers,staffkm-tenant}
mkdir -p packages/ts/{ui-kit,api-types,sdk,design-tokens}
mkdir -p packages/sql/migrations
mkdir -p tools/{codegen,scripts,docker,e2e}
git mv docker-compose.yml docker-compose.override.yml infra/
# 修正所有 import path（用 sed）
find services -name "*.py" -exec sed -i '' 's|from core\.|from staffkm_core.|g' {} +
```

## 5. 替代方案

| 方案 | 優點 | 缺點 | 為何不選 |
|------|------|------|----------|
| Nx | 強大快取、affected 分析 | 太重、學習曲線 | overkill |
| Turborepo | 流行、快 | Python 支援弱 | 我們是雙語 |
| 多個 repo（polyrepo） | 隔離強 | 共享 type 麻煩、版本同步難 | 微服務但同一團隊 |
| **pnpm + uv workspace（本案）** | **輕量、原生工具** | 需自寫 affected 邏輯 | **採用** |

## 6. 風險與緩解

| 風險 | 機率 | 衝擊 | 緩解 |
|------|------|------|------|
| 重組打斷既有 CI/CD | 高 | 中 | 分支執行、跑完 E2E 才合併；保留舊路徑 symlink 過渡 |
| Import path 全壞 | 確定 | 中 | 自動化 sed + 完整 grep 驗證；ruff check 強制 |
| Docker context 路徑改變 | 確定 | 中 | Dockerfile 同步更新；docker compose 新加 context |
| 開發者 git log 找不到歷史 | 中 | 低 | 用 `git mv` 而非刪除新增，blame 可追蹤 |

## 7. 影響範圍

- **檔案移動**：~200 個 .py + ~150 個 .vue/.ts，全部用 git mv
- **CI**：workflow 路徑大改，需先在 fork 驗證
- **Docker build context**：所有 service 的 `context:` 從 `.` 改為 `services/<name>`
- **開發者本機**：要重新 `pnpm install` + `uv sync`

## 8. 推出計畫

- [ ] **Stage 1**（W1 Mon）：開 `feature/v2-monorepo` branch，執行遷移腳本
- [ ] **Stage 2**（W1 Tue-Wed）：修 import、修 Docker、跑單元測試
- [ ] **Stage 3**（W1 Thu）：跑完整 E2E、確認 docker compose up 成功
- [ ] **Stage 4**（W1 Fri）：merge to main、宣布凍結 v1 結構
- [ ] **Stage 5**（W2）：所有人 rebase、補修 import 殘留

回滾：feature branch 沒合就棄；合了就 revert PR + 重新 git mv 回去（用 git log 追溯）。

## 9. 量測指標

- 遷移完成日：W1 Fri 前
- CI 全綠：100%
- import 錯誤：grep 後 = 0
- 開發者 onboarding 時間：< 30 分鐘（從 clone 到 dev 環境跑起）

## 10. 開放問題

- [ ] Q1：apps/web 要不要 SSR？（影響部署複雜度）→ 由 RFC-004 解答
- [ ] Q2：tools/e2e 用 Playwright 還是 Cypress？@ux to recommend
- [ ] Q3：要不要直接上 Turbopack？@lead-fe 評估

## 11. 參考資料

- [pnpm Workspaces](https://pnpm.io/workspaces)
- [uv Workspaces](https://docs.astral.sh/uv/concepts/workspaces/)
- [Vercel Monorepo Guide](https://vercel.com/docs/monorepos)
- 相關：RFC-004 (Nuxt migration)
