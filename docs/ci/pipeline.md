# CI Pipeline 說明

## 1. 流程

```
push / PR  →  changes (path filter)
                ├─ backend?  → backend job  (ruff + mypy + pytest + codecov)
                ├─ frontend? → frontend job (lint + type-check + test + build)
                └─ always   → security job  (Trivy + Gitleaks，PR only)
                ↓
              ci-pass gate（必通過才能 merge）

push main only:
              e2e job (docker compose up → wait-healthy → playwright)
```

## 2. 各 job 內容

### backend
- 依賴：`uv sync --all-extras`
- gate：
  - `ruff check .`
  - `ruff format --check .`
  - `mypy services packages/python` (strict)
  - `pytest --cov --cov-fail-under=80`
- 服務：postgres:pgvector + redis（service container）

### frontend
- 依賴：`pnpm install --frozen-lockfile`
- gate：
  - `pnpm -r lint` — 目前為 stub（後續 PR 接 eslint）
  - `pnpm -r type-check` — vue-tsc --noEmit
  - `pnpm -r test` — 目前為 stub（後續 PR 接 vitest）
  - `pnpm -r build` — 確保 production build 不掛

### security
- Trivy filesystem scan：CRITICAL / HIGH 直接 fail
- Gitleaks：掃 secret pattern

### e2e（main-only）
- `docker compose up` → `tools/scripts/wait-healthy.sh` → playwright
- 失敗時上傳 `playwright-report` artifact

## 3. 本 PR 增補

- `tools/scripts/wait-healthy.sh` — CI / dev 共用
- `tools/e2e/`：Playwright skeleton（package.json + config + smoke.spec.ts）
- `services/agent/tests/test_smoke.py` — 確保模組可 import、registries 健康
- `apps/web/package.json` 補 `type-check / lint / test` script

## 4. 後續

| Backlog                      | 影響                                |
| ---------------------------- | ----------------------------------- |
| eslint + vue-eslint-parser   | 取代 lint stub                      |
| vitest + @vue/test-utils     | 取代 test stub；目標 50% 覆蓋率     |
| 各 service 補 pytest         | 目前只有 agent；knowledge/auth/chat |
| codecov badge                | 公開覆蓋率                          |
| Playwright 場景擴充          | login → create app → chat 完整流程 |

## 5. 加速建議

- backend: `uv` cache 已啟用
- frontend: `pnpm-store` cache via `actions/setup-node@v4 cache:'pnpm'`
- 用 path filter 跳過無關 job（已實作）
