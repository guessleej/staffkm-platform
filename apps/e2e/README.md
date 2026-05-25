# staffKM E2E Tests

> v3.0 — Playwright-based P0 critical-path test suite（6 specs）。

## 安裝

```bash
cd apps/e2e
pnpm install
pnpm exec playwright install chromium    # 第一次只裝 chromium 即可
```

## 跑

```bash
# 本機（dev server 必須跑著）
pnpm test                  # headless
pnpm test:headed           # 看瀏覽器
pnpm test:debug            # 單步 debug

# 看 HTML 報告
pnpm report
```

環境變數：
- `STAFFKM_BASE_URL` (預設 `http://localhost`)
- `STAFFKM_ADMIN_USERNAME` (預設 `admin`)
- `STAFFKM_ADMIN_PASSWORD` (預設 `Admin@2026`)

## 6 個 spec

| # | 檔 | 內容 |
|---|---|---|
| 01 | login.spec.ts | admin 登入成功 + 錯密碼出 error |
| 02 | captcha.spec.ts | 4 次失敗觸發 CAPTCHA + GET /auth/captcha |
| 03 | app-crud.spec.ts | /applications render + ?tour=templates 自動開模板畫廊 |
| 04 | knowledge.spec.ts | /knowledge render + 透過 API 建 KB → 列表看到 |
| 05 | widget.spec.ts | /widget.js + /widget-demo.html 載入無 JS 錯誤 |
| 06 | chat-render.spec.ts | 對話渲染 last-mile：攔截串流餵 gemma4 風格純換行 token → 斷言 marked→DOM 分明（<ol>/<li>/<br>），不擠成一坨（守 SSE 換行回歸史 v5.9.32~v5.11.8）|

## CI 整合

`.github/workflows/e2e.yml`（未來 PR 加）：
1. `docker compose up -d`
2. 等 healthy
3. `pnpm test --reporter=junit`
4. fail 上傳 `playwright-report/` artifact

## 加新 spec 慣例

- 檔名 `NN-{場景}.spec.ts`
- describe 開頭標 `P0` / `P1` / `P2` 重要性
- 重要 API call 用 `request.fixture` 而非走 UI（速度）
- 避免共用 admin 帳號做負面測（用 `e2e_${timestamp}` 假帳號）

## Known gotchas

- CAPTCHA Redis 計數 10 min 才過期；test 間清 Redis 或用獨立 username
- /chat 串流回應慢；spec 03 暫不真打串流，只驗頁面 render
- Workflow editor 載入 600KB lf-vendor，timeout 設長一些
