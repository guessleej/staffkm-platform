# Distributed Workers — v4.0 P3 / P4

把 v3.6 的 5 個 in-process asyncio worker loop 搬到 **arq + Redis** 上，agent
service 可以水平 scale 而不會重複觸發 trigger / dispatcher。

## 為什麼是 arq

| 候選 | 評估 |
|---|---|
| **arq** ✅ | async-native（不用 wrap）/ Redis-backed / 內建 cron / ~500 行 / 已有 Redis 基礎建設（v3.0-P1 CAPTCHA）|
| Celery | 同步起家、async 支援是後補的；要多 broker 配置（rabbit/redis）；功能太多用不到 |
| RQ | 沒有 async-native；要 process worker；cron 要外加 RQ-scheduler |
| Temporal | 太重 — 要跑 Temporal server，學習曲線高；保留給有狀態 saga 需求 |

決策：v4.0 範圍夠小、async-native 是硬需求 → arq。

## 架構

```
                    ┌──────────────────────────────────────────┐
                    │              Redis (db 2)                 │
                    │  arq:queue (zset) ── job records         │
                    └──────────────────────────────────────────┘
                            ▲                  ▲
                            │ enqueue          │ pop + run
                            │ (cron / RPC)     │
                            │                  │
      ┌────────────────────┴────┐   ┌──────────┴───────────────┐
      │  agent service (FastAPI) │   │  worker service (arq)    │
      │  WORKER_BACKEND=arq      │   │  python -m arq           │
      │  → 不啟 in-process loop  │   │  app.workers.arq_settings│
      └──────────────────────────┘   │  .WorkerSettings         │
                                     └──────────────────────────┘
                            ▲
                            │
                            │  /api/v1/admin/workers/{backend,queue}
                       admin client
```

## 5 個 job ↔ 原 loop 對應表

| arq job | 對應 v3.6 loop | cron schedule | 等效 interval_sec |
|---|---|---|---|
| `trigger_scan_job` | `trigger_worker_loop` | every minute | 60s |
| `trigger_dispatch_job` | `trigger_dispatcher_loop` | every 10s | 10s |
| `resume_check_job` | `resume_worker_loop` | every 30s | 30s |
| `quota_alert_job` | `alert_worker_loop` | every 10 min | 600s |
| `webhook_dispatch_job` | `webhook_dispatcher_loop` | every 30s | 30s |

每個 job 內部只做「一輪」工作；節奏由 arq 的 `cron_jobs` 控制。

## 啟用方式

### Docker compose（dev / single-host prod）

```bash
echo "WORKER_BACKEND=arq" >> .env

# 1) 先 redeploy agent service（讓 in-process loop 關閉）
./tools/scripts/safe-redeploy.sh agent

# 2) 起 worker container（profile = arq-worker，opt-in）
docker compose --profile arq-worker up -d worker

# 3) 驗證
curl -H "X-User-Roles: admin" -H "X-User-ID: <admin-uuid>" \
     http://localhost/api/v1/admin/workers/backend
# {"data": {"backend": "arq"}}

curl -H "X-User-Roles: admin" -H "X-User-ID: <admin-uuid>" \
     http://localhost/api/v1/admin/workers/queue
# {"data": {"backend": "arq", "queue_depth": 0}}
```

### K8s（Helm）

> v4.0 P4 範圍縮窄；Helm chart 改動留下版 PR。
> 目前 K8s 部署仍是 `WORKER_BACKEND=inprocess` 預設。

## 回退（rollback）

```bash
# .env 改回（或拿掉那行）
sed -i.bak '/^WORKER_BACKEND=/d' .env

# 關 worker container
docker compose --profile arq-worker rm -sf worker

# redeploy agent → in-process loop 自動回來
./tools/scripts/safe-redeploy.sh agent
```

## ⚠️ 兩個 backend 不能同時跑

`inprocess` + `arq` 並存會 race：

- `trigger_dispatcher` 兩邊都會 `FOR UPDATE SKIP LOCKED` 同一張 `event_trigger_runs`
- `resume_worker` 兩邊會 race approve / reject
- `webhook_outbox` 兩邊都 claim → 可能 double-send webhook（外部端 idempotent 才安全）

切換時務必：
1. 改 `.env` `WORKER_BACKEND`
2. 先 stop 舊 backend（agent redeploy OR `compose rm worker`）
3. 再 start 新 backend

## 觀測

- `GET /api/v1/admin/workers/backend` — 回目前 backend
- `GET /api/v1/admin/workers/queue` — arq 模式回 Redis `arq:queue` zset 深度（inprocess 回 `null`）
- worker container 的 stdout（structlog）
- v3.6 P2 `worker_heartbeats` 表仍由 inprocess loop 寫；arq backend 下心跳改看 worker stdout（v4.0-PR4 會把心跳 import 進每個 arq job）

## 不在此 PR 範圍

- Helm chart 改動（worker Deployment）→ 下版 PR
- Grafana arq dashboard（queue depth / processed rate / failed jobs）→ 下版 PR
- per-job Prometheus metric → 下版 PR

## 程式碼地圖

- `packages/python/staffkm-core/staffkm_core/utils/arq_settings.py` — `REDIS_SETTINGS` 共用
- `services/agent/app/workers/arq_settings.py` — `WorkerSettings` + 5 個 job
- `services/agent/app/main.py` — lifespan feature flag（`WORKER_BACKEND`）
- `services/agent/app/api/admin_workers.py` — admin 狀態 API
- `services/gateway/app/routers/_generic_proxy.py` — gateway proxy
- `services/agent/app/core/trigger_worker.py` — 新加 `_scan_due_triggers(session)` helper
- `infra/docker-compose.yml` — `worker` service（profile `arq-worker`）
