# RFC-012 — Observability Stack（M5 GA）

| 項目      | 內容                                       |
| --------- | ------------------------------------------ |
| 狀態      | Draft（M5 GA：基礎設施 + 指標規格上 main） |
| 提案日期  | 2026-05-16                                 |
| 對應里程碑 | M5 GA v2.0.0                              |
| 相關 PR   | feat/m5a-observability                     |

## 1. 動機

v2.0 上線後需要回答四個問題：
1. **是否健康**：服務有沒有掛、5xx 是不是飆
2. **是否慢**：哪個 endpoint p95 > SLO
3. **是否貴**：哪個 workspace / model 燒最多 token
4. **是否在跑**：trigger worker / queue 有沒有 stall

不裝堆疊就只能事後撈日誌、推臆，無法做 SLO / on-call。

## 2. 架構

```
service ─OTLP gRPC/HTTP→ OTel Collector ─┬→ Prometheus (metrics)
                                          ├→ Jaeger (traces)
                                          └→ stdout (debug / dev)

Prometheus ─→ Grafana dashboards
Prometheus ─→ alertmanager → Slack / PagerDuty
```

## 3. 三類訊號

### 3.1 Metrics（必有）

Service-level（已部分接，prometheus_client）：
- `http_requests_total{job, method, route, status}`
- `http_request_duration_seconds_bucket{job, route}`

業務（M5 GA 新增）：
- `staffkm_model_usage_total{workspace, provider, model}`        — 來自 usage log（counter）
- `staffkm_workflow_node_duration_seconds_bucket{node_type}`
- `staffkm_pgvector_query_ms_bucket{kb_id}`
- `staffkm_trigger_worker_last_scan_ts`                          — 用來偵測 stall

### 3.2 Traces（新接）

對所有 API endpoint 做自動 instrument（`opentelemetry-instrumentation-fastapi`），加：
- workflow execution → 每 node 一個 span
- LLM call → adapter 內 span（含 model / tokens）
- DB query → SQLAlchemy 自動 span（slow query > 50ms 標 warning）

### 3.3 Logs（已有 structlog）

僅補：
- 在 log entry 自動帶 `trace_id` / `span_id`（由 OTel context 注入）
- 採樣率：dev 全收、prod error 全收 + info 20%

## 4. SLO（先列出，逐月校正）

| Service      | SLI                  | SLO                     | 燒錯預算               |
| ------------ | -------------------- | ----------------------- | ---------------------- |
| gateway      | availability         | 99.9% / 月              | 43 min                 |
| chat (SSE)   | TTFT (first token)   | p95 < 2s                | 5% 違反                |
| knowledge    | pgvector p95         | < 50ms（百萬筆）         | 5% 違反                |
| workflow     | node fail rate       | < 1%                    | 1% 違反                |
| trigger      | scan lag             | < 90s                   | 嚴格 0%                |

## 5. 本 PR 範圍

- `infra/monitoring/otel-collector-config.yaml`
- `infra/monitoring/alerts.yml`（ServiceDown / 5xx / p95 / pgvector / quota / worker stall）
- `infra/monitoring/grafana/dashboards/staffkm-overview.json`
- RFC（本文）

**下一輪**（M5 中段）：
- 各服務裝 `opentelemetry-instrumentation-fastapi` + `opentelemetry-exporter-otlp`
- 將 usage log 同步輸出 Prometheus counter
- docker-compose 加 otel-collector + jaeger service
- runbook：常見 alert 處理流程

## 6. 風險

- **trace 採樣不當會塞爆 Jaeger**：prod 預設 1% tail-based sampling，error 100%。
- **prometheus 拉取 metrics 過頻會吃 CPU**：scrape_interval 15s 已足；高負載再降到 30s。
- **PII**：trace span attributes 嚴禁帶使用者 query / 文件內容（只帶 IDs + 大小）。
