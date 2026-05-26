# 全棧負載壓測 — harness + runbook（k6）

> **狀態：工具就緒，尚未對 served stack 真跑。** 本檔提供可直接執行的 k6 harness
> （`tools/perf/load_test.js`）+ runbook，指向**已部署的** staffKM stack（gateway + 各
> service 全跑）。**沒有**在本機產出「跑過」的數字——因為全棧 HTTP 壓測需要 served
> 環境（staging / prod-like），不是單機容器能如實代表的。
>
> 已**真跑過**的是 **DB 層**規模驗證：`tools/perf/scale_validation.py`（100k 段落 pgvector，
> 見 `docs/perf/v5.12-scale-validation.md`）。本檔補的是它**上面**那層（gateway→service→DB
> 的端到端 HTTP）。兩者互補：DB 層證向量檢索可承量，全棧層證 API 端到端在負載下的 p95/錯誤率。

## 為什麼不在本機「假跑」

單機 docker compose 把所有 service 擠在同一台、共用 CPU/記憶體，壓出來的 p95/吞吐**不能**
代表 production（多副本、獨立資源、真網路）。硬要在本機跑只會得到誤導數字。誠實作法：
**交付可執行工具 + runbook，標清前置條件**，由有 staging/prod-like 環境的人對真環境跑。

## 安裝 k6

```bash
brew install k6            # macOS
# 或 docker run --rm -i grafana/k6 run - < tools/perf/load_test.js
```

## 跑法

```bash
# A) 帳密登入（harness 自動取 token）
k6 run -e BASE_URL=https://staffkm.staging.example.com \
       -e USERNAME=loadtest -e PASSWORD='***' -e WORKSPACE_ID=<uuid> \
       -e SEARCH_KB_ID=<kb-uuid> \
       -e VUS=50 -e DURATION=3m tools/perf/load_test.js

# B) 直接給 token（跳過登入）
k6 run -e BASE_URL=... -e TOKEN=<jwt> -e WORKSPACE_ID=<uuid> -e VUS=50 -e DURATION=3m tools/perf/load_test.js

# C) 完全不給憑證 → 只壓 /health 基線（量 gateway 純轉發吞吐）
k6 run -e BASE_URL=... tools/perf/load_test.js
```

## 情境 / 門檻（env 可調）

| env | 預設 | 說明 |
|---|---|---|
| `BASE_URL` | `http://localhost` | 目標 gateway base URL |
| `USERNAME`/`PASSWORD` 或 `TOKEN` | — | 認證；都不給 → health-only |
| `WORKSPACE_ID` | — | workspace-scoped 端點需要（CLAUDE.md §7）|
| `SEARCH_KB_ID` | — | 設了才壓知識檢索（RAG hot path）|
| `VUS` | 20 | 穩態並發 virtual users |
| `DURATION` | 1m | 穩態時長（前後各 `RAMP` 爬升/降載）|
| `P95_MS` | 800 | **通過門檻**：http_req_duration p95 |
| `ERROR_RATE` | 0.01 | **通過門檻**：失敗率 < 1% |

- **只讀情境**（health / list conversations / knowledge search）——刻意不做寫入/刪除，
  避免污染目標環境。要壓寫入路徑請另開情境並用拋棄式 workspace。
- threshold 沒過 → k6 退非零（可進 CI gate / 發版前 gate）。

## 建議壓測階梯

| 階 | 目的 | 設定 |
|---|---|---|
| smoke | 驗 harness + endpoint 通 | `VUS=1 DURATION=30s` |
| load | 預期尖峰負載下的 p95 | `VUS=<預期尖峰> DURATION=5m` |
| stress | 找拐點（吞吐飽和 / 錯誤率爬升）| `VUS` 階梯加大直到 threshold 破 |
| soak | 找記憶體洩漏 / 連線池耗盡 | `VUS=<中等> DURATION=2h` |

## 讀數字

- `http_req_duration p(95)`：端到端延遲（含 gateway→service→DB→LLM）。對照 DB 層 100k
  規模驗證（單查 p50 ~35ms@probes=10）→ 全棧多出的就是 gateway/service/序列化/網路開銷。
- `http_req_failed` / `staffkm_errors`：錯誤率。爬升點 = 容量上限。
- 分端點 Trend（`lat_list_conversations` / `lat_knowledge_search` / `lat_health`）：哪條路徑先撐不住。
- throughput（iterations/s、http_reqs/s）：k6 summary 末尾。

## 已知前置 / 注意

- 目標環境要有 **loadtest 帳號** + 一個可查的 **KB**（SEARCH_KB_ID）才壓得到 RAG 路徑。
- 若打 prod，先確認**配額 / rate-limit / quota**不會把壓測流量誤判為濫用（quota 是 soft cap，
  見踩雷集；大量並發可能短暫超發）。建議對 staging 或隔離 workspace 壓。
- LLM 節點會真的呼叫模型 → 壓 chat/stream 會產生**真實 token 成本**；本 harness 預設**不**壓
  stream（只 list/search），要壓 generation 請明確加情境並評估成本。
