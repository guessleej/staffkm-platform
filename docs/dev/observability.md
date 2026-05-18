# Observability — Tracing + Logs（v3.3 B1/B2）

staffKM 在 v3.3 引入 **OpenTelemetry tracing (Tempo) + Loki log aggregation**，補齊 Prometheus metrics 之外的兩支柱。預設關閉，要 opt-in 才會跑（多耗 ~600 MB RAM）。

## 元件總覽

| 元件 | 角色 | Profile |
|---|---|---|
| Prometheus | metrics（已 GA v2.2） | `monitoring` |
| Grafana | dashboards / explore | `monitoring` |
| **Tempo** | OTLP traces 收集 + 查詢 | `observability` |
| **Loki** | 集中 log 索引 | `observability` |
| **Promtail** | 從 Docker socket 抓 staffkm-* 容器 log 推到 Loki | `observability` |

## Opt-in

```bash
# 1. .env 取消註解
OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4318

# 2. 啟動（monitoring + observability 一起）
docker compose --profile monitoring --profile observability up -d
```

啟動後：

- Grafana：http://localhost:3000（admin / 見 `.env`）
- Tempo HTTP：http://localhost:3200
- Loki HTTP：http://localhost:3100
- OTLP receiver：http://localhost:4318/v1/traces（service container 走 `http://tempo:4318`）

## Datasource 對照

Grafana 已 provisioned：

| Name | uid | URL |
|---|---|---|
| `staffkm-tempo` | `staffkm-tempo` | http://tempo:3200 |
| `staffkm-loki` | `staffkm-loki` | http://loki:3100 |
| `staffkm-prometheus`（既有） | `prometheus` | http://prometheus:9090 |

## Auto-instrumentation 範圍

`packages/python/staffkm-core/staffkm_core/observability.py` 提供 `setup_otel()` + `instrument_fastapi()`，6 個 service lifespan 已接：

- FastAPI request span（排除 `/metrics`、`/health`）
- httpx outbound（service ↔ service）
- asyncpg query
- structlog 自動帶 `trace_id` / `span_id`（透過 `LoggingInstrumentor`，**不**覆寫 format → JSON 保留）

env `OTEL_EXPORTER_OTLP_ENDPOINT` 沒設就 noop，本機 dev / unit test 不會噴 connection error。

## Demo：從一個 5xx log 跳到對應 trace

1. Grafana → **Explore** → 選 `staffkm-loki` datasource
2. Query：`{service="agent"} |= "level=error"`（或用 `|= "5"` 找 5xx）
3. 點開某筆 log → 右側 panel 看到 `TraceID` derived field（regex `trace_id=(\w+)` 自動抽）
4. 點 `TraceID` → 跳到 `staffkm-tempo` 顯示完整 span tree（gateway → agent → knowledge → asyncpg）
5. 反向：在 Tempo trace view 點 service tag → 用 `tracesToLogsV2` 跳回 Loki 該 service 對應時段 log

## 保留期

- Tempo blocks：7 天（`compactor.compaction.block_retention: 168h`）
- Loki：7 天（`limits_config.retention_period: 168h`）

local dev 不需要動；prod 想加大改 yaml 後 `docker compose restart tempo loki`。

## 關閉

```bash
docker compose --profile observability down
# 或暫停 instrumentation：.env 註解掉 OTEL_EXPORTER_OTLP_ENDPOINT 後 restart service
```

OTel 失敗永遠不阻塞 app 啟動（`setup_otel` 內 try/except + log.error）。

## B3 — Exemplar 接線（v3.3）

Prometheus datasource provisioning（`grafana/datasources/prometheus.yml`）已加：
```yaml
jsonData:
  exemplarTraceIdDestinations:
    - name: trace_id
      datasourceUid: staffkm-tempo
```

要在自訂 dashboard panel 啟用 exemplar 顯示：
1. PromQL target 加 `"exemplar": true`
2. panel `fieldConfig.defaults.custom.showPoints: "always"`
3. Prometheus 端要有帶 `trace_id` exemplar label 的 metric（OTel auto-instrument 對 FastAPI histogram 會自動帶）

範例見 `v3-observability-demo.json` 的 "p95 latency" panel。

既有的 v3-traffic / v3-endpoints / v3-resource / v3-llm-usage 等沒主動加 exemplar；想啟用就在 targets 加 `"exemplar": true` 即可（不破壞既有顯示）。

## B4 — Observability Demo dashboard

`v3-observability-demo.json`（uid `staffkm-v3-obs-demo`）展示三向跳轉：
- **Logs panel (Loki)** — 最近 staffkm-* 容器 error log；JSON 內 `trace_id` 自動轉 `TraceID` derived field、點即跳 Tempo
- **5xx rate + p95 latency (Prometheus + exemplar)** — 圖上 exemplar 點直接跳對應 trace
- **Service map (Tempo nodeGraph)** — service 拓樸 + 平均延遲

Grafana → Dashboards → "staffKM v3.3 — Observability Demo" 直接看。

