# Observability & QA Plan

> Sprint 20 跳過項目的執行藍圖。等流量上來、或上 production 前完成。

## A. Metrics Dashboard

### 現有資料源
- `usage_log` table (PR #155 已通)：per-request timestamp, user, app, tokens (in/out), cost, latency, status
- structlog JSON logs in all containers
- `event_trigger_runs` (PR #151)：trigger 執行紀錄
- celery task results in Redis backend
- DB tables：applications / knowledge_bases / documents / conversations 計數

### 建議 stack
| 層 | 選擇 | 為什麼 |
|---|---|---|
| 時序資料 | **Prometheus** | scrape 模式適合 multi-svc，已有 `/metrics` endpoint 預留 |
| 可視化 | **Grafana** | 多面板 + alert + 免費 |
| App metrics | **prometheus-fastapi-instrumentator** | 5 行接，自動 endpoint timing |
| Log 查詢 | **Loki** (option) | 跟 Grafana 整合，省一個服務 |

### 5 個一定要的 dashboard panel
1. **流量總覽**：requests/min by service (gateway / agent / knowledge / chat / auth)
2. **LLM 用量**：daily tokens + cost by workspace（從 usage_log）
3. **錯誤率**：4xx / 5xx by endpoint，最近 1h
4. **延遲分佈**：p50 / p95 / p99 by endpoint
5. **Background tasks**：celery queue length + task duration distribution

### 落地步驟（半天）
1. 加 `prometheus-fastapi-instrumentator` 到 gateway/agent/knowledge requirements
2. 各 service `app.main:app` 接 `Instrumentator().instrument(app).expose(app)`
3. docker-compose 加 prometheus + grafana services
4. 進 grafana provisioning 自動載入 5 個 dashboard json
5. nginx 加 `/grafana/` proxy (admin-only)

## B. E2E Test

### Critical path
| Path | 步驟 | 重要性 |
|---|---|---|
| **Login flow** | /login → 帳號密碼 → /chat | 🔴 P0 |
| **Login + CAPTCHA** | 故意錯 3 次 → 應出 captcha → 答對才能登 | 🔴 P0 |
| **Create KB + upload** | /knowledge → 建立 → 上傳 PDF → status ready | 🔴 P0 |
| **Web sync** | /knowledge → web 模式 + URL → doc 出現 | 🟠 P1 |
| **Create App + chat** | /applications → 新增 → /chat → 收到回應 + citation | 🔴 P0 |
| **Template flow** | /apps → 從模板 → 建立 → chat | 🟠 P1 |
| **Project scope** | /projects → 建 + attach KB → /chat 應帶 KB | 🟠 P1 |
| **Admin set quota** | /admin/usage → 設 cap → 之後 chat 應檢 quota | 🟡 P2 |

### 建議 stack
- **Playwright** (TS)：跟 frontend 同語言、screenshot diff、video 錄影
- 跑在 CI (GitHub Actions) `services` 起 docker-compose + 跑 e2e specs
- 本地：`pnpm test:e2e` 直接打 dev server

### 落地步驟（一天）
1. `apps/e2e/` 新 package：playwright init + playwright.config.ts
2. 跨 P0 path 寫 5 個 spec：login / create-kb-upload / create-app-chat / captcha / quota-exceed
3. CI：`.github/workflows/e2e.yml` — docker compose up → wait healthy → run playwright
4. fail 時自動 attach screenshot/video artifact

## 時程估算
- Metrics dashboard：**半天** (4h)
- E2E 5 specs + CI：**一天** (8h)
- 合計 1.5 個工作天

## 為何現在不做
1. **流量小**：dashboard 沒資料看也沒意義
2. **功能仍快速迭代**：E2E spec 改太勤反而拖累
3. **上 production 前必做**：當作 release gate

## 觸發信號
- 內測 ≥ 10 個真實用戶 / 周
- 上 production 前 1-2 週
- 累積 ≥ 3 個 regression bug
