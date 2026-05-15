# Coding Standards — staffKM v2

## Python（後端）

- **格式**：Ruff format（取代 black + isort）
- **lint**：Ruff（含 pyflakes/pycodestyle/bugbear/simplify）
- **型別**：mypy strict（`disallow_untyped_defs = true`）
- **版本**：Python 3.12+；async-first；FastAPI dependency injection
- **命名**：`snake_case` 函式 / `PascalCase` 類別 / `UPPER_SNAKE` 常數
- **結構**：module-level 公開 API 寫在 `__init__.py`；私有以 `_` 前綴
- **錯誤**：自訂 exception 繼承 `StaffKMError`；不直接 raise `Exception`
- **DB 查詢**：必走 `WorkspaceScopedQuery` helper；禁直接 `select(Model)`（lint rule 禁止）
- **記憶體**：批次處理用 generator / async iterator，不要 `list(...)` 全載入
- **I/O**：同步 I/O（PIL、subprocess）一律走 `asyncio.to_thread`

## TypeScript（前端）

- **格式**：Prettier
- **lint**：ESLint（@typescript-eslint + vue + tailwind plugin）
- **型別**：`strict: true`；禁 `any`（用 `unknown` 配合 narrowing）
- **版本**：TypeScript 5.5+；Node 20 LTS；pnpm 9+
- **命名**：`camelCase` / `PascalCase` Vue component / `kebab-case` 檔名
- **API call**：一律走自動產生的 SDK，禁手寫 fetch
- **i18n**：禁字面字串（lint rule 偵測）

## Vue 3 / Nuxt 3

- **Composition API + `<script setup lang="ts">`** only
- **元件名稱** 兩個字以上（避免和 HTML 衝突）
- **Props** 用 `defineProps<{ ... }>()`；不寫 runtime declaration
- **State** Pinia store；禁 mutation 散落 component
- **CSS** Tailwind utility-first；複雜的進 `<style scoped>` + `@apply`

## SQL / Migration

- **遷移檔** Alembic auto-gen 後**人工檢查**；禁 raw `op.execute("ALTER ...")` 沒附 down
- **欄位命名** `snake_case`；FK `<table>_id`
- **索引** 規範：`idx_<table>_<col>` / `uniq_<table>_<col>` / `gin_<table>_<col>`
- **時間欄** `TIMESTAMPTZ`，預設 `now()`
- **soft delete** 用 `deleted_at`（NULL = 存在）

## Git / Commit

- **branch**：`feat/<topic>` / `fix/<bug>` / `chore/<task>` / `rfc/<n>`
- **commit**：Conventional Commits（`feat: ...` / `fix: ...` / `BREAKING CHANGE:`）
- **size**：單一 PR < 400 行 diff；超過拆分
- **rebase** before merge；禁 merge commit 進 main

## 文件

- **API endpoint** 必含 OpenAPI summary + description + 範例
- **Public function** 必有 docstring（Google style）
- **每個 RFC merge 後** 30 天內補 `docs/adr/`
- **CHANGELOG** 每次 release 自動產（用 release-please）

## 測試

- **覆蓋率** ≥ 80%（每模組）
- **命名** `test_<behavior>_when_<condition>`（Given-When-Then）
- **fixture** 共用放 `conftest.py`；test data 用 factory（factory-boy）
- **E2E** 每個 milestone 必補主要 user journey

## 安全

- **Secret** 一律走環境變數 / Vault；禁進 git（gitleaks CI 把關）
- **依賴** 每週 Renovate / Dependabot；CVE high 24h 內修
- **輸入** Pydantic / zod 驗證；禁信任 client
- **輸出** HTML escape（Jinja autoescape on / Vue 自動）
- **密碼** Argon2id；JWT HS256 → 將升 RS256
