# Changelog

依 [Keep a Changelog](https://keepachangelog.com/) 與 SemVer。

## [3.0.0] — 2026-05-18

> **Production Hardening** milestone — 第一個 major release。
> 重點：把 v2.x 累積的技術債（in-process state、LegacyURLBridge、無 audit 軌跡、缺 E2E 自動化）一次清掉，
> 為長期 multi-tenant production 部署打下基礎。

### Highlights
- 🔐 **Auth hardening** — CAPTCHA 計數搬到 Redis（多 instance safe）+ OIDC schema 正規化（`oidc_sub` / `oidc_issuer`）
- 🌉 **LegacyURLBridge sunset path** — 新增 `LEGACY_URL_MODE` 環境變數（rewrite / 410 / off），預告 v3.x 拔除
- 📜 **Audit log API + UI** — `/admin/audit-logs` 可查、可篩、workspace-scoped；前端 admin 介面
- 📊 **5 個 Grafana dashboard** — traffic / endpoints / resource / LLM usage / celery
- 🎭 **Playwright E2E** — 5 個 P0 critical-path spec（login / captcha / app / kb / widget）

### Added — Auth hardening (v3.0-P1, PR #176)
- `services/auth`：
  - `_fail_count` / `_fail_record` / `_fail_clear` 改 async + Redis backed
    （key: `staffkm:auth:fail:{ip}:{username.lower()}`，TTL 10 min，原子 INCR+EXPIRE pipeline）
  - Redis 不可用時 fallback in-process dict（不阻塞登入）
  - `User` model 加 `oidc_sub: String(256, index=True)` + `oidc_issuer: String(256)`
  - `_AUTH_BOOTSTRAP_DDL` 加 3 條 `ALTER TABLE ADD COLUMN IF NOT EXISTS` + 1 條 backfill
    （`UPDATE users SET oidc_sub = SUBSTRING(ldap_dn FROM 6) WHERE ldap_dn LIKE 'oidc:%'`）
  - OIDC callback：優先 `oidc_sub` lookup、fallback email；email-only 老帳號首次 SSO 自動補 `oidc_sub`
- `services/agent` middleware `LegacyURLBridge`：
  - 新環境變數 `LEGACY_URL_MODE`
    - `rewrite`（預設，v2.x 相容）— `/api/v1/{prefix}/...` → `/api/v1/workspace/{ws}/{prefix}/...`
    - `410` — 回 `410 Gone` + `Link: <new_url>; rel="successor-version"`
    - `off` — bypass
  - 預告：v3.x 之後 default 改 `410`、v4.x 完全移除

### Added — Audit log + Grafana (v3.0-P2, PR #177)
- `services/agent/app/api/audit.py`（新）：
  - `GET /api/v1/workspace/{ws}/admin/audit-logs?actor=&action=&resource=&since=&page=&page_size=`
  - 沿用既有 partitioned `audit_logs` table，SELECT alias 補相容欄位名
  - workspace-scoped where：`(workspace_id = :ws OR workspace_id IS NULL)`
  - `_record()` helper 給其他 endpoint 寫入（INSERT 用 `CAST(NULLIF(:ip, '') AS inet)`）
- DDL：`audit_logs` ALTER 加 `workspace_id` / `actor_username` / `entity_label` + 2 index
- Gateway proxy：`/api/v1/admin/audit-logs` → agent service
- Legacy bridge `_LEGACY_PREFIXES` 加 `/api/v1/admin/audit-logs`
- 前端 `apps/web/src/views/admin/AuditLogsView.vue`：
  - Action / Entity filter chips、分頁、JSON detail expandable
  - action badge 顏色（create / delete / update / login）
- Grafana dashboards（`infra/monitoring/grafana/dashboards/v3-*.json`）：
  - `v3-traffic` — 5xx rate / RPS / latency p50/p95/p99
  - `v3-endpoints` — top endpoints by request / error
  - `v3-resource` — CPU / RSS / open FD（用 `process_*` 系列）
  - `v3-llm-usage` — token 用量（PG datasource）
  - `v3-celery` — 任務 queue lag（celery-exporter）

### Added — Playwright E2E (v3.0-P3, PR #178)
- `apps/e2e/`（新 package `@staffkm/e2e`，`@playwright/test ^1.49.0`）：
  - `playwright.config.ts` — workers=1（CAPTCHA 隔離）、`trace: retain-on-failure`、baseURL from `STAFFKM_BASE_URL`
  - `fixtures/admin.ts` — `loginAsAdmin(page)` helper
  - 5 個 P0 spec：
    - `01-login` — admin 登入 + 錯密碼出 error
    - `02-captcha` — 4 次失敗觸發 `captcha_required`（用 `e2e_${timestamp}` 隔離）
    - `03-app-crud` — `/applications` render + `?tour=templates` 自動開模板畫廊
    - `04-knowledge` — KB 列表 + API 建 KB → 列表看到
    - `05-widget` — `/widget.js` + `/widget-demo.html` 載入無 JS 錯誤
- `README.md`：env 變數、CI 整合骨架、加新 spec 慣例、known gotchas

### Changed
- Auth service lifespan 加跑 `_run_auth_bootstrap_ddl()`（OIDC 欄位 idempotent migration）
- `services/agent/app/main.py` `include_router(audit.router)` 掛 `/admin/audit-logs`
- Gateway `_generic_proxy.py` 加 `audit_logs_router`

### Breaking Changes（forward-looking）
- ⚠️ **`LEGACY_URL_MODE` 環境變數**：本版仍預設 `rewrite`，**v3.x 之後將改 `410`、v4.0 移除 bridge**
  - 影響：所有直接打 `/api/v1/{prefix}/...`（沒帶 workspace）的 client（含 gateway proxy / 前端）需在 v3.x 內逐步改打 workspace-scoped URL
  - 建議：開發環境提早設 `LEGACY_URL_MODE=410` 找出殘留 caller
- ⚠️ **OIDC user schema**：舊 `users.ldap_dn = 'oidc:{sub}'` 的記錄在啟動時會自動 backfill 到 `oidc_sub`；新 SSO 不再寫 `ldap_dn`
  - 上線後 `ldap_dn` 對 OIDC 帳號不再更新；reporting 請改讀 `oidc_sub` / `oidc_issuer`

### Migration（從 v2.5 升 v3.0）
1. **DB**：什麼都不用做。Auth + Agent service 啟動時跑 idempotent DDL，自動補 `users.oidc_sub` / `audit_logs.workspace_id` 等欄位 + backfill。
2. **Redis**：CAPTCHA 計數現在會用 DB 3；確保 `REDIS_PASSWORD` 設好（compose 已內建）。Redis 掛掉會 fallback in-process，不阻塞登入。
3. **Frontend**：admin 角色登入後左側 nav 多 `/admin/audit-logs`，無需重設權限。
4. **E2E**：`cd apps/e2e && pnpm install && pnpm exec playwright install chromium && pnpm test`。
5. **Grafana**：5 個 dashboard JSON 放在 `infra/monitoring/grafana/dashboards/v3-*.json`，provisioning 已 mount，restart Grafana 即看到。

### PR refs
#175（roadmap）/ #176（auth hardening）/ #177（audit + dashboards）/ #178（Playwright E2E）

---

## [2.5.0] — 2026-05-17

> **Developer partners** milestone — CLAUDE.md / API ref / template marketplace。
> 重點：把 staffKM 變成可以「跟其他 dev / AI 助理協作」+ 「生態擴散」的平台。
> v2.x roadmap 完成。

### Highlights
- 🧠 **CLAUDE.md** — repo-level project memory，凝結 Sprint 14-25 設計決策 + 踩雷集 + 風格慣例
- 📘 **API reference 完整 doc** — 7000 字、12 個資源組、SSE 範例、SDK
- 🌍 **Template marketplace** — 跨 workspace 分享模板 + 安裝計數 + install button

### Added — CLAUDE.md (v2.5-A)
新檔 `CLAUDE.md`（repo root）：
- 10 個重要原則（compose / Auth / Design system / Icon / Nav / routing 三層 / SQL CAST / DDL / perf 等）
- 常用指令 + Repo 結構地圖
- **8 條踩雷集**（不要再踩）
- 命名 / commit / PR 風格
- 重要 PR / Tag 對照表
- 跟使用者溝通方式 + 不要做的事

下次任何 Claude session 進這個 repo 就有完整上下文，不必重新摸索。

### Added — API reference (v2.5-B)
`docs/dev/api-reference.md` — 7000 字：
- 3 種認證方式（JWT / API Key / 公開）
- 12 個資源組 endpoint 全表（applications / kbs / docs / chat / templates / mcp / triggers / memories / usage / projects / public / app-templates）
- 統一回應格式 + SSE streaming JS / Python SDK 範例
- Rate limit / OpenAPI / Webhook / 變更日誌

### Added — Template marketplace (v2.5-C)
- DDL：`workspace_app_templates` + `is_public` + `install_count` cols
- 新 endpoints：
  - `GET /api/v1/app-templates/marketplace` — 跨 workspace 列出 public 模板（排 install_count DESC）
  - `POST /api/v1/app-templates/marketplace/{id}/install` — 複製到自己 workspace + install_count++
- TemplateCreate / Update / Out 加 `is_public` + `install_count`
- 前端 api 加 `listMarketplace()` / `installFromMarketplace()`

### v2.x roadmap 完成

| Tag | 主題 | 範圍 |
|---|---|---|
| v2.0 | GA | 105+ PRs，5 milestone |
| v2.1 | Functional parity | MaxKB 缺口 5/5 + Orphan 5 模組 + Design system v2 |
| v2.2 | Production-ready | metrics + TLS + backup |
| v2.3 | Demo polish | onboarding + citation chip |
| v2.4 | B2B | widget + SSO + user docs |
| v2.5 | Dev partners | CLAUDE.md + API ref + marketplace |

### PR refs
#173

---

## [2.4.0] — 2026-05-17

> **B2B enablement** milestone — embed widget + SSO + user docs。
> 重點：把 staffKM 變成可以「放心嵌入 / 接客戶 SSO / 給最終使用者看手冊」的元件。

### Highlights
- 🪟 **Embeddable widget** — 一行 `<script>` 嵌任何網站，6 KB vanilla JS
- 🔐 **OIDC SSO** — Google / Microsoft AD / Okta / Azure AD；最小 lift（無 DB schema 改）
- 📖 **8 篇 user-guide** — first-login / chat / KB / app / project / web-sync / embed / admin + FAQ

### Added — Embeddable Widget (v2.4-A)
- `apps/web/public/widget.js` — 6 KB vanilla JS、無依賴
  - data-app-id / data-host / data-position / data-color / data-label
  - 公開 API：`staffKM.open() / close() / toggle()`
  - Lazy mount iframe + ESC / 點空白關 + RWD
- `apps/web/public/widget-demo.html` — 互動測試頁
- `PublicChatView`：`?embed=1` → 精簡 chrome（小 header / 隱藏 Powered by chip）
- nginx + Caddy：`/widget.js` / `/widget-demo.html` / `/share/*` 允許 cross-origin iframe
  - `X-Frame-Options` 拿掉，改 `CSP frame-ancestors: *`

### Added — OIDC SSO (v2.4-B)
- `services/auth/app/api/oidc.py`：
  - `GET /info` — 前端探 SSO 啟用 + 顯示名
  - `GET /login` — redirect IdP authorize（state cookie + JWT-signed nonce 防 CSRF）
  - `GET /callback` — code → token → userinfo → upsert User → 簽 staffKM JWT → redirect 帶 `#access_token`
- 6 個新 `OIDC_*` config vars（.env.production.example 完整範例）
- 標準 OIDC discovery（抓 `/.well-known/openid-configuration`）
- Match by email；新 user auto-create role=`user`（`OIDC_DEFAULT_ROLE`）
- 借用 `user.ldap_dn` 欄存 `oidc:{sub}`（避免 DB schema migration）
- Gateway PUBLIC_PATHS 加 3 個 oidc 端點
- Frontend：
  - `api/auth.ts`: oidcInfo() / oidcLoginUrl()
  - LoginView mount 時讀 `#access_token` hash（callback redirect）→ 直接登入
  - 「使用 SSO 登入」按鈕（OIDC_ENABLED=true 才出現）

### Added — User docs (v2.4-C)
8 篇繁中 markdown（5000+ 字）：

| 檔 | 對象 | 內容 |
|---|---|---|
| README | index | 章節對照 + 一句話介紹 |
| 01-first-login | 新人 | 登入 / 導覽 / locale / theme |
| 02-chat | 使用者 | 對話 / citation chip / artifact 展開 / Project scope |
| 03-knowledge-base | 使用者 | 建 KB / 上傳 / 切片 / 命中測試 |
| 04-create-app | 建立者 | 模板 / 空白 / Workflow / 存模板 / 分享 / API |
| 05-projects | 進階 | Project 概念 / 加資源 / 切換 / 管理 |
| 06-web-sync | 進階 | 3 種模式（單 URL / 多 URL / sitemap）+ upsert |
| 07-embed-widget | 整合 | snippet + 全部選項 + API + 安全 + demo |
| 08-admin | admin | users / models / usage quota / 進階模組 / 監控 |
| 99-faq | 全 | 13 個常見問題 |

### Configuration

```env
# .env.production 加（OIDC 啟用範例）
OIDC_ENABLED=true
OIDC_DISPLAY_NAME=Google
OIDC_ISSUER=https://accounts.google.com
OIDC_CLIENT_ID=...apps.googleusercontent.com
OIDC_CLIENT_SECRET=GOCSPX-...
OIDC_REDIRECT_URI=https://staffkm.example.com/api/v1/auth/oidc/callback
OIDC_SCOPES=openid email profile
OIDC_DEFAULT_ROLE=user
```

### PR refs
#171 (all 3 in one PR)

---

## [2.3.0] — 2026-05-17

> **Demo polish** milestone — onboarding wizard + citation chip UI。
> 重點：first-run 體驗、chat 引用視覺升級。Demo-friendly。

### Highlights
- 👋 **Onboarding wizard** — first-run 3 步驟導覽（welcome / pick path / KB hint），skip 隨時可
- 💬 **Citation chip + hover preview** — 從原本 list 升級為 inline brand chip + 深色 popover 顯示內容片段

### Added — Onboarding (PR #169)
- `components/onboarding/OnboardingWizard.vue` — 3 步驟、進度條、ESC/skip 友好
- 兩條路徑：
  - 「✨ 從模板」→ `/applications?tour=templates` → 自動開模板畫廊
  - 「⚡ 空白」→ `/applications?tour=create` → 自動開建立 dialog
- localStorage `staffkm.onboarding.done` 不重複跑
- DashboardLayout mount + 只在 auth.user 存在時自動跑
- `defineExpose({ open() })` 給 settings menu 「重看導覽」

### Changed — Citation UI (PR #169)
- ChatView 助理訊息引用區從 border-left `<ul>` 升為 inline `<div>` chip group
- Chip 樣式：`bg-brand-50/60` + 編號圓圈 + doc_name truncate + 相符度
- Hover popover：深色背景 (`bg-neutral-900`) + 內容 `line-clamp-6` + 三角箭頭
- Click 行為不變 — 仍打開 ArtifactPane 看完整內容

### PR refs
#169

---

## [2.2.0] — 2026-05-17

> **Production-ready** milestone — 3 個 PR 把 dev compose 推向「能上 production」。
> Foundation for B2B 客戶部署 + 雲端 multi-tenant SaaS deployment。

### Highlights
- ✅ **All 6 services 都 expose `/metrics`** — gateway 早有，補上 agent/knowledge/chat/auth/integration
- 🔒 **Production overlay + Caddy auto-TLS** — `--prod` 一鍵切換 dev / prod；Let's Encrypt + HTTP/3 + 完整 security headers
- 💾 **完整備份 / 還原 SOP** — PG + MinIO daily snapshot + DR drill 季度節奏

### Added — Observability (v2.2-A, PR #165)
- `prometheus-fastapi-instrumentator` 加到 5 個 service requirements
- 各 main.py 加 `Instrumentator().instrument(app).expose(app, endpoint="/metrics")`
- 6/6 service 都有 `/metrics`；prometheus profile 啟動後 5/7 targets up（postgres/redis 之後加 exporter）

### Added — Production deploy (v2.2-B, PR #166)
- `infra/docker-compose.production.yml` overlay：
  - DB/Redis/MinIO 收斂不對外
  - nginx → **Caddy 2.8**（auto-TLS + HTTP/3 QUIC）
  - 全部 `restart: always` + memory limits
  - monitoring profile 預設啟動
- `infra/caddy/Caddyfile`：
  - Let's Encrypt 自動證書（90 天續訂）
  - SSE-friendly：`flush_interval=-1` + `read_timeout 600s`
  - 全套 security headers (HSTS / XFO / CSP / Permissions-Policy)
  - Grafana `/grafana/*` basic-auth 二層保護
  - `www.{$DOMAIN}` → 主 domain redirect
- `.env.production.example`：完整 secrets 模板
- `tools/scripts/safe-redeploy.sh --prod` flag：一行切 dev / prod
- `docs/deploy/production-deploy.md`：完整 runbook（前置 / init / 維運 / TLS / secret / DR / FAQ）

### Added — Backup & Restore (v2.2-C, PR #167)
- `tools/backup/backup-postgres.sh` — daily 02:00、`pg_dump --format=custom -Z 9`、保留 14 daily + 8 weekly、可推 S3
- `tools/backup/backup-minio.sh` — daily 02:15、`mc mirror --remove`、保留 14 份
- `tools/backup/restore-postgres.sh` — 互動式選 dump、DROP+CREATE、平行 jobs=4、verify table count
- `tools/backup/restore-minio.sh` — 互動式 mirror（無 --remove 防誤刪）
- `tools/backup/crontab.example` — daily cron + hourly stale-check（>26h 沒備就 ALERT）
- `docs/deploy/backup-restore.md` — TL;DR 一次性設定 + 3 個還原場景（誤刪 / 整台重灌 / 選擇性 table）+ DR drill SOP（季度）+ checklist

### Changed
- `safe-redeploy.sh` 加 `--prod` 旗標，自動切到 `.env.production` + production overlay

### 上 production 流程

```bash
# 一次性
cp .env.production.example .env.production
vi .env.production   # 填 PUBLIC_DOMAIN / ADMIN_EMAIL / secrets
sudo crontab -e      # 貼 tools/backup/crontab.example
sudo mkdir -p /var/lib/staffkm/backups/{postgres,minio}
sudo chown -R 999:999 /var/lib/staffkm/backups/postgres

# 啟動
./tools/scripts/safe-redeploy.sh --prod --all
# 等 1-3 分鐘 Caddy 拿 LE 證書，DNS 必須先指好

# 驗證
curl -I https://staffkm.example.com   # HTTP/2 200
```

### Migration

無 breaking。若已上 v2.1，照以下步驟升 v2.2：
1. `git pull` 最新 main
2. （已有 prod 環境）`./tools/scripts/safe-redeploy.sh --prod --all`
3. （首次上 prod）按上方流程

### PR refs
#165 (metrics) → #166 (prod compose) → #167 (backup)

---

## [2.1.0] — 2026-05-17

> 「GA 後第一個產品輪」— 20 個 PR、6 個 Sprint（14-20）、一天密集迭代。
> 重點：對標 MaxKB 5 缺口全關 + 5 個 orphan endpoint 模組曝光 + Design system v2 +
> Auth 強化 + Perf 三連跳 + i18n 三語系。

### Highlights
- **MaxKB-parity 5 缺口全關**：模板中心 + Web KB + ArtifactPane + Project 抽象 + 簡易建立
- **5 個 orphan endpoint 模組曝光**：MCP / Triggers / Workflow Versions / Usage Quota / Memory / Task Revoke（CRUD 真.通，含 backend routing 三層修補）
- **Design system v2 全面落地**：dark mode 100% token-flip、SIcon 44 names、ui-kit 34 元件、Storybook gallery
- **Auth 強化**：CAPTCHA 防暴力 + 401 interceptor 並發去重 + `?next=` 導回
- **Perf 三連跳**：ChatLayout **1022→9 KB** (-99%) / md-vendor **1009→200 KB** (-80%) / WorkflowEditor **66→33 KB** (-50%)
- **i18n 三語系**：繁中 / 簡中 / 英文

### Added — MaxKB-parity

- 📦 **Application 模板中心 + 6 種子模板**（#139）— 內部問答 / 客服 FAQ / 合約審閱 / SQL 助手 / 內訓教練 / 文件翻譯
- 🎮 **「立即試用」preview chat**（#145）— `/applications/preview/chat` 端點，無持久化、不計 usage
- 🌐 **Web KB 同步**（#137 早 + #141 follow-up + **#159 sitemap.xml**）— 單 URL / 多 URL 批次 / sitemap.xml recursive 一層
- 🗂 **Project 抽象 UX 全鏈**（#144 + **#158 chat scope binding**）— picker 上 DashboardLayout / `/projects` 管理頁 / 卡片 attach button / active Project KB 自動進 RAG
- 📝 **Workspace 自訂模板庫**（#157）— App 卡片「存模板」、gallery 合併 built-in + workspace
- ✨ **ArtifactPane**（#140）— marked + highlight.js + 複製 + ESC + 訊息一鍵展開

### Added — Orphan endpoints 5 模組

- 🔗 **MCP Servers Store UI**（#148）— 7 endpoints（CRUD + refresh + tools 列表 + call tool）
- 🔄 **Triggers UI**（#151）— 5 endpoints + 3 種 kind chip（interval/cron/webhook）+ runs drawer
- 📂 **Workflow Versions panel**（#154）— 3 endpoints + 右側 drawer + 「節點版本」按鈕（與既有「應用版本」並列）
- ✕ **Task Revoke**（#154）— admin 在卡住的 doc 上看到取消按鈕
- 💰 **Usage Quota UI**（#153 修 routing）— 既有 view 補上 quota 設定（端點之前 404）
- 🧠 **Memory UI**（#160）— scope filter（全部/我的/應用/團隊）+ 關鍵字搜尋 + importance slider

### Added — Design system v2

- 🎨 **SIcon 元件**（早 + 多 sprint follow-up）— 44 個 lucide-style icons + currentColor + spin
- 📐 **Typography utility classes** — `.text-h1/h2/.../body/.../caption` 全域
- 🖼 **SEmpty 4 種插圖** — box/search/doc/plus
- 📚 **Storybook Gallery**（早）— 34 元件一頁掃完 + 44 icon 預覽

### Added — Auth

- 🛡️ **CAPTCHA 登入**（#161）— 連 3 次失敗強制要求數學 CAPTCHA（10 分鐘窗口，per-IP per-username）
- 🔁 **401 interceptor 強化**（#156）— 並發 401 共用同一個 refresh、防遞迴、`?next=` 帶回原路徑

### Added — i18n

- 🇨🇳 **簡中 (zh-CN)** locale（#160）— pickInitialLocale 偵測 `zh-cn` / `zh-hans` / `zh-sg`

### Changed — UX / Design system

- **Nav 重構**（#143 + **#150**）— `/skills` `/tools` `/data-sources` `/mcp/servers` `/triggers` `/memories` 從「進階 ▼」下拉 → icon-only nav + hover tooltip（拿掉 60 行 dropdown 程式碼）
- **WorkspaceSwitcher / ProjectPicker / Modal** 全套 SIcon 化
- **ChatView 助理訊息**（#140）— hover 出「📤 展開」按鈕（≥600 字或含 ``` 才顯示）
- **Page transition**（#159）— 安全版（watch + CSS key toggle，無 Transition mode='out-in'，不會 race）+ scroll-top

### Fixed — Dark mode

- 🌓 **Dark mode token 100% coverage**（#142 + #147 + **#149**）— `bg-white` / `text-gray-*` / `text-slate-*` 全 0 殘留；**反轉 neutral 階層**一次修 352 處 hardcode
- WorkflowEditor 寫死 `#f0f2f5` 背景修為 `bg-surface-sunken`

### Fixed — Backend routing & schema

- **Gateway 沒 mount usage/triggers/mcp/memories**（#153）— 補 4 個 generic proxy
- **Agent LegacyURLBridge 缺 prefix**（#153）— 補 usage/triggers/mcp/memories/model-providers/media-providers/app-templates
- **Usage router mount prefix 缺 `/usage`**（#153）
- **MCP create SQL syntax**（#155）— asyncpg dialect 對 `:param::jsonb` 處理 bug，改 `CAST(:param AS jsonb)`
- **long_term_memories legacy schema**（#155）— 加 6 個 ALTER TABLE ADD COLUMN IF NOT EXISTS + user_id UUID 型別轉換

### Performance

- **ChatLayout 1022→9 KB** (-99%)（#146）— ArtifactPane defineAsyncComponent + `v-if="artifact.isOpen"`
- **md-vendor 1009→200 KB** (-80%)（#146）— `highlight.js/lib/common` 替代預設 192 languages
- **WorkflowEditor 66→33 KB** (-50%)（#162）— NodeConfigPanel defineAsyncComponent
- 拆 vendor chunks：`md-vendor`、`lf-vendor`、`vue-vendor`

### Docs

- `docs/qa/dark-mode-checklist.md`（#147）
- `docs/qa/visual-sweep-sprint19-20.md`（#163）
- `docs/plans/observability-plan.md`（#163）— metrics dashboard + E2E test 落地藍圖
- `docs/plans/next-direction.md`（#163）— 14 個下一步選項 + 4 推薦組合 + 4 anti-rec
- ui-kit README + Storybook 修 build（早期 + #138）

### Removed

- 「進階 ▼」 dropdown component（#150）— 改為 4 個 icon-only nav
- 多餘 `advancedOpen` state / `onClickOutside` / `isAdvancedActive` computed

### Security

- CAPTCHA 防暴力登入（#161）
- 401 interceptor 防遞迴 / 並發去重（#156）
- `?next=` redirect 限制必須 `/` 開頭（防 open redirect）

### Lessons learned（教訓）

- **「empty state ≠ 真.通」** — PR #148 / #151 前端 UI 落地後仍 404，因為 routing 沒接。教訓：endpoint UI 落地前 至少 curl 一次 POST/PUT。
- **Design system alias > raw scale** — 352 處 `bg-neutral-200` hardcode 不會 flip；改 11 行 token 反轉 neutral 階層比改 352 行 .vue 安全。
- **「做完忘了曝光」很容易發生** — 7 個 mcp endpoint + 3 個 trigger 隔離功能完全沒入口。Audit router 表 → orphan 5 模組曝光 5 PR。

### Migration（v2.0 → v2.1）

無 breaking change。所有 DDL 是 idempotent ALTER。可直接 `safe-redeploy.sh --all`。

唯一注意：若 `long_term_memories` 表是 v2.0 之前建的（schema 不齊），bootstrap_ddl 會自動補欄位 + UPDATE 補預設 workspace_id。

### PR refs（按 merge 時序）

#139 #140 #141 #142 #143 #144 #145 #146 #147 #148 #149 #150 #151 #152 #153 #154 #155 #156 #157 #158 #159 #160 #161 #162 #163

---

## [2.0.0] — 2026-05-17（GA）

> staffKM v2 — Enterprise AI Knowledge Management Platform
> 105+ PR、14 RFC、5 milestones（M1~M5）全部達標的 GA。

### Highlights

- **企業級多租戶**：workspace + 4 階 RBAC + 三層資料隔離（Path/RBAC/SQL）
- **30+ Workflow Nodes**：含 5 種 Workflow Manager（simple / retry / parallel / batch / sandbox）
- **25+ Model Providers**：地端 Ollama 預設；專屬 adapter for Anthropic / Gemini / Cohere / Bedrock / Vertex AI / MiniMax；其餘走 OpenAI-compatible
- **5+ Media Providers**：DALL-E / Stability / Whisper / OpenAI TTS / ElevenLabs
- **Token 計帳 + Quota**：tiktoken 精算、月度 cap、429 hard-limit、Admin dashboard
- **Sandbox 隔離**：subprocess + rlimit + timeout（RFC-010）；M4-A 升 nsjail
- **完整 Observability**：OTel collector + Prometheus + Grafana + Jaeger（RFC-012）
- **長期記憶 / 排程觸發 / MCP Hub**：M4 啟動
- **完整文件**：personas / brand guide / 12 篇 user/admin/dev guide / Backup-DR runbook
- **Python SDK + admin CLI**：`pip install staffkm-sdk staffkm-cli`
- **Helm chart**：HPA + SSE-friendly ingress + secret 管理

### Added — 完整功能清單

**M1（多租戶 + Folder + 設計系統）**
- workspace + member + role 表 + middleware（PR #51~54）
- 三層隔離（Path / RBAC / SQL ScopedQuery）
- Generic CRUD factory 雙端（make_crud_router / makeCrud<T,C,U>）
- 4 種模組：Tool / Skill / Data Source / Folder（PR #61~70）
- D-1 Tool 試跑、D-2 Skill 模板、D-3 DataSource 連線測試、D-4 share link、D-5 folder、D-6 markdown、D-7 application 版本控制
- i18n zh-TW / en 雙語字典（PR #98）
- Brand Guideline v1 + logo SVG + favicon（PR #99）
- UX 研究（personas / interview template / JTBD 對照）（PR #100）
- 設計系統 v1.1：⌘K Command Palette + dark mode token alias（PR #101）

**M2（Workflow Engine v2）**
- 30+ node types 與 dispatch（PR #75）
- 5 種 Workflow Manager（PR #76 + #82：parallel/batch 真實 asyncio.gather）
- LogicFlow 編輯器升級：undo/redo + snap + clipboard + 快捷鍵（PR #91）
- Sandbox 隔離（subprocess + rlimit）+ shell 節點 + RFC-010（PR #92）
- Workflow 版本控制

**M3（Model Hub）**
- BaseProvider 抽象 + 25 family registry + RFC-009（PR #79）
- 7 家專屬 adapter：Anthropic / Gemini / Cohere / Bedrock / Vertex AI / MiniMax + OpenAI-compat（PR #86 #87 #89）
- application_agent 接 get_adapter()（PR #86）
- Admin UI 串 registry 下拉（PR #83）
- Token 計帳 + Workspace Quota（PR #84）
- chat_stream 接 record_usage + 429 quota check（PR #88）
- 用量儀表板 UI（/admin/usage）（PR #90）

**M4（進階能力 — 啟動）**
- Media Provider 抽象（DALL-E/Stability/Whisper/TTS/ElevenLabs）（PR #93）
- Long-term Memory Store（DDL + CRUD + 全文搜尋）（PR #94）
- Event Triggers + 60s background worker（PR #95）
- MCP Hub（servers + tools cache + JSON-RPC client）（PR #96）
- 整合層 RFC-011（PR #97）

**M5（GA Release）**
- OTel collector + 6 條 alert + Grafana dashboard + RFC-012（PR #106）
- Helm chart 雛形 + Backup/DR runbook（PR #107）
- Python SDK + admin CLI + OpenAPI dump 腳本（PR #108）
- VitePress docs site + 12 篇 guide（PR #109）
- Demo seeder + Marketing landing（PR #110）

**工程基礎**
- CI（pytest + ruff + mypy + vue-tsc + Playwright + Trivy + Gitleaks）— PR #102
- pgvector 壓測腳本 + 報告模板（PR #103）
- API key Fernet 加密層（PR #104）
- tiktoken 精確計費（PR #105）

### Changed
- 從 v1 對話介面整體重構為對話為中心（claude.ai 對標）
- LegacyURLBridge：v1 → workspace-scoped 自動重寫，Deprecation header
- 全域 alert/confirm 部分替換為 useToast / useDialog（A11y dialog）

### Security
- API key 預設走 Fernet 對稱加密（環境變數 `STAFFKM_SECRETS_KEY`）
- Workflow `shell` 節點僅在 `workflow_manager='sandbox'` 下執行
- argv 必須絕對路徑；rlimit + timeout 強制
- Quota 超額 hard-cap 429（不只 warning）
- 多租戶三層隔離，每個 query 經 `WorkspaceScopedQuery`

### Known limitations
- **trigger_worker 多副本**：目前單副本（advisory lock 留 v2.1）
- **MCP server SSRF**：尚無 outbound allow-list（留 v2.1）
- **dark mode 全量化**：tokens 就位，部分 view 仍寫死 `text-gray-*`（清單在 `docs/design/dark-mode-checklist.md`）
- **eslint / vitest**：CI 為 stub（type-check vue-tsc 已強制）
- **embedding memory recall**：M4 啟動只有全文檢索，向量檢索留 M4 中段

### Migration（v1.x → v2.0）
1. `helm upgrade` 會自動跑 `bootstrap_ddl`（idempotent）
2. v1 URL 仍可訪問（LegacyURLBridge 重寫 + Deprecation header）；建議 90 天內客戶端切到 v2 URL
3. 既有 application 的 model 設定自動沿用；無 provider_type 走 OpenAI-compat fallback
4. API key 既有 base64 / 明文資料相容；逐步走 `encrypt_secret` 替換

## v1.x（legacy）

見 `docs/legacy/CHANGELOG-v1.md`（保留歷史；v2 GA 後不再 backport）。
