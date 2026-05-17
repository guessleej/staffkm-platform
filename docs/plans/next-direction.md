# 下一個方向 — 選項清單

> 19 個 PR 跑完 + 5 個方向結算後的可能下一步。
> 每個選項標示**範圍 / ROI / 前置依賴**幫助決定。

## A. 產品 — 把 first-run 體驗推到「dazzle me」

### A1. 範本入口提到 onboarding
- 新人第一次登入時跳 onboarding wizard：選個模板 → 建一個 demo KB → 直接 chat 看效果
- 範圍：M（onboarding component + step state）
- ROI：高 — first-impression 決定留存

### A2. 訊息引用 (citation) UI 升級
- 目前 citation 是 plain list；升級成 inline chip + hover preview
- 範圍：M（ChatView + Citation component + popover）
- ROI：高 — 是 RAG 賣點

### A3. App 模板 marketplace（跨 workspace 分享）
- 把 workspace 模板加 public 開關，做一個全平台模板瀏覽頁
- 範圍：L（新 backend + permission + UI）
- ROI：中 — 早期沒 critical mass

## B. 整合 — 把 staffKM 變成「能放心嵌入」的元件

### B1. Embeddable chat widget (`<script src="...">`)
- 一行 JS 嵌任何網站（員工 portal / 客戶官網）
- 範圍：M（dist 一個 standalone bundle + Public iframe app + theming param）
- ROI：高 — 銷售場景常被問

### B2. LINE / Teams bot bridge
- 後端已有 `/integrations/line/webhook` 預留，但沒接 message handler
- 範圍：M-L（要熟 LINE messaging API + webhook signature）
- ROI：高（B2B 客戶常用）

### B3. SSO (OIDC / SAML)
- 接 Microsoft AD / Google Workspace
- 範圍：L（auth service 大改）
- ROI：高（企業客戶 hard requirement）

## C. 部署 — 從「dev compose」走到「production deploy」

### C1. Production docker-compose
- 拆 .env 為 .env.production，docs 寫 secret 管理
- TLS 通過 caddy / Let's Encrypt
- 範圍：S（半天）
- ROI：高（沒這個沒法上）

### C2. Kubernetes Helm chart
- 給跨 instance 部署（HA 多副本）
- 範圍：L（auth/session 都得 stateless）
- ROI：中（小型部署不需要）

### C3. Backup & restore playbook
- postgres + minio 備份腳本 + restore drill
- 範圍：S（一個 cron + 文件）
- ROI：高（uptime 信心）

## D. 文件

### D1. CLAUDE.md 升級
- 把 Sprint 14-20 的決策、design system v2、orphan-audit 教訓寫進去
- 範圍：S（半天）
- ROI：中 — 下個對話開始就有用

### D2. End-user docs（給最終使用者看的 manual）
- 怎麼建 KB / 設 App / 用 chat / 自訂模板…
- 範圍：M
- ROI：高（B2B 入庫必備）

### D3. API reference site
- 已有 /api/docs (FastAPI swagger)，包裝一層 prose
- 範圍：S
- ROI：中（SDK 客戶才在乎）

## E. 觀察性（已有 plan，照表行）

見 `docs/plans/observability-plan.md`。
**Trigger 時機**：內測 ≥ 10 用戶 / 上 production 前 2 週。

## 推薦組合

| 場景 | 建議 |
|---|---|
| **本週 demo / 內部展示** | A1 onboarding wizard + A2 citation UI |
| **要簽 B2B 客戶** | B1 embeddable widget + B3 SSO + D2 user docs |
| **要上 production** | C1 prod compose + C3 backup + E 觀察性 |
| **要拉開發合作夥伴** | D1 CLAUDE.md + D3 API ref + A3 marketplace |

## Anti-recommendation（建議**不**做的事）

| 事 | 為什麼不 |
|---|---|
| **重寫成 Next.js / SvelteKit** | 目前 Vue 3 / Vite 沒明顯瓶頸，重寫換不來價值 |
| **加更多 LLM provider** | M3 已有 10+，再加是 long-tail |
| **微服務再拆** | 已 6 個 service，再拆 ops 變痛 |
| **行動 App** | PWA 從現有 web 就行，原生 App 不划算 |
