# Load Test Plan v1.0（v2.0 GA pre-release）

> 目標：在 stage 環境模擬「中型企業 500 人 + 高峰並發 50 對話」場景，
> 找出 SLO 邊界、瓶頸服務、需擴展的 component。

## 1. 目標 SLI

| SLI                         | 目標                | 不過 → 怎麼辦       |
| --------------------------- | ------------------- | ------------------- |
| Gateway availability        | 99.9% / 1h          | 加副本 + ingress    |
| Chat TTFT (first token)     | p95 < 2s            | LLM provider 降階   |
| Knowledge search            | p95 < 50ms（百萬筆） | pgvector tune       |
| Workflow node              | p95 < 1s（除 LLM）   | profile slow node   |
| 5xx error rate              | < 0.1%              | 阻擋 release        |

## 2. 場景

### S1 — 對話高峰
- 50 並發使用者
- 每人 10 輪對話、間隔 30s
- model：Ollama gemma4:e4b（地端）
- 持續 30 min
- 預期：chat-stream 100% 成功；TTFT p95 < 2s

### S2 — 知識庫檢索壓測
- 100k chunks / 1M chunks 兩檔（用 `tools/bench/pgvector_bench.py`）
- ef_search = 64
- 1000 queries（500 concurrent）
- 預期：p95 < 50ms（100k）、< 100ms（1M）

### S3 — Workflow batch
- 一個 workflow 帶 `map` 節點處理 1000 items
- workflow_manager = batch，chunk_size = 10
- 預期：總時長 < 簡易 simple 模式的 50%（≥ 2× speedup）

### S4 — Quota stress
- workspace_id 設 token cap 10,000
- 灌 100 個請求各 200 tokens
- 預期：前 ~50 個成功，之後全部 429（且 stream 仍可完成）

### S5 — Trigger storm
- 建 100 個 interval=10s 的 trigger
- 跑 10 min（共 ~6000 fire 期望）
- 預期：trigger_worker_last_scan_ts 永遠 < 90s 滯後

## 3. 工具

| 場景 | 工具                          |
| ---- | ----------------------------- |
| S1   | k6 + xk6-sse                  |
| S2   | tools/bench/pgvector_bench.py |
| S3   | curl + jq + workflow API      |
| S4   | k6                            |
| S5   | 內建 worker + Prometheus 看 scan_ts |

## 4. 環境

```
stage cluster
├─ 3 × agent (HPA 2-10)
├─ 3 × gateway
├─ 2 × knowledge
├─ 1 × Ollama（地端 gemma4:e4b）
├─ Managed Postgres + pgvector（4 vCPU / 16 GB / SSD）
└─ Prometheus / Grafana / Jaeger
```

預算：~$200 / 月（停測即關）

## 5. 出口條件（Go / No-Go）

- [ ] 所有 SLI 達標 → **Go**
- [ ] 任一 SLI 失敗 → 找 root cause，修，重測；不阻擋 release 但寫 `docs/release/known-issues.md`
- [ ] 5xx > 1% / panic / OOM → **No-Go**，必修

## 6. 報告

每場景跑完寫一行到 `docs/release/load-test-results.md`：

```md
| 日期       | 場景 | 持續 | 結果                          | 備註 |
| ---------- | ---- | ---- | ----------------------------- | ---- |
| 2026-05-17 | S1   | 30m  | TTFT p95=1.4s ✓, 5xx=0.02% ✓  |      |
```
