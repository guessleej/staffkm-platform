# Definition of Done — staffKM v2

> 一個 Story 在以下 **全部** 條件成立時才能 close 並 merge。Reviewer 用此清單檢核。

---

## 1. 程式碼

- [ ] 通過 lint（Ruff for Python、ESLint + Prettier for TS）
- [ ] 通過型別檢查（mypy strict、vue-tsc）
- [ ] 自動化測試覆蓋本次改動 ≥ 80%（unit + integration）
- [ ] 沒有 `console.log` / `print()` 殘留 debug 碼
- [ ] 沒有 hard-coded secret、API key、URL（用 env var）

## 2. 測試

- [ ] 寫了 unit test 覆蓋核心邏輯
- [ ] 寫了 integration test 覆蓋資料庫 / API 互動
- [ ] 重要 user journey 寫了 E2E test（Playwright）
- [ ] 本機 `make test` 全綠
- [ ] CI pipeline 全綠

## 3. 安全

- [ ] 通過 Bandit / npm audit / Trivy 掃描
- [ ] 新增的 endpoint 有正確的 authn / authz
- [ ] 使用者輸入有驗證（Pydantic / zod）
- [ ] DB query 用 ORM 或 parameterized SQL（杜絕 SQL injection）
- [ ] 沒有暴露內部錯誤訊息到 client（生產環境）

## 4. 文件

- [ ] 對應 RFC（若是重大改動）已 merge 並標 Accepted
- [ ] OpenAPI spec 自動更新（drf-spectacular / FastAPI）
- [ ] README / CHANGELOG 更新
- [ ] 公開 API 有 docstring 與範例
- [ ] 若改動 DB schema，補一份 migration 說明

## 5. 可觀測性

- [ ] 關鍵路徑有 structured logging（含 trace_id、tenant_id）
- [ ] 新增的 metric 已加入 Prometheus（counter / histogram）
- [ ] error path 有 `log.error` 並含完整 context

## 6. 效能

- [ ] N+1 query 已用 `select_related` / `prefetch_related` 處理
- [ ] 大資料量操作有 pagination 或 streaming
- [ ] 同步 I/O 不在 async path（已用 `asyncio.to_thread`）
- [ ] 必要時跑 k6 confirm 沒有 regression

## 7. UX 與 i18n

- [ ] 對 UX 改動：Figma 設計稿已 merge
- [ ] 文字字串走 i18n（zh-TW 至少齊全）
- [ ] empty / loading / error / success 4 種狀態都實作
- [ ] 對行動裝置可用（Phase 5 要求）

## 8. 部署

- [ ] Dockerfile 健康（image size 沒爆增）
- [ ] docker-compose / Helm chart 已更新
- [ ] 環境變數新增已寫入 `.env.example`
- [ ] DB migration script reversible
- [ ] 回滾步驟已記錄於 PR description

## 9. PR 流程

- [ ] PR 標題用 conventional commit 格式（`feat:` / `fix:` / `chore:` …）
- [ ] PR description 含：why / what / how / testing / screenshots
- [ ] 至少 1 名 owner 通過（重大改動 ≥ 2 名）
- [ ] 連結到對應 issue（自動 close）
- [ ] 衝突已 rebase
- [ ] commit message 乾淨（squash 或 rebase）

---

## 例外處理

若 Story 無法完全滿足 DoD（如 hotfix、spike），須：
1. 在 PR 註明哪些項目 skip 與原因
2. 建立 follow-up issue 追蹤補齊
3. PMP 同意才能 merge
