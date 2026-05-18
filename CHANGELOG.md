# Changelog

依 [Keep a Changelog](https://keepachangelog.com/) 與 SemVer。

## [3.8.0] — 2026-05-18

> **v3.7 留尾收口** milestone — workflow conv_id / per-user billing / multi-judge / query plan analyzer。
> **v3.x 系列收尾完成**。

### Highlights
- 🧵 **Workflow conv_id** — WorkflowExecutor 接收 conversation_id，sub_workflow 繼承
- 💵 **Admin billing UI** — 跨 ws per-user 報表（list / detail / CSV 匯出）
- 🧑‍⚖️ **Multi-judge consensus** — `rag_eval` 支援多個 judge，consensus + stdev 反映分歧度
- 🔬 **Query plan analyzer** — slow query → 自動 EXPLAIN → admin 看完整 plan

### Added — Workflow conv_id (v3.8-P1, PR #224)
- `WorkflowExecutor.__init__` 加 `conversation_id` keyword-only
- 7 meter call site 全部帶 `conversation_id=self.conversation_id`（LLM × 3 + media × 4）
- `workflows.py /chat`：`WorkflowChatRequest` 加 `conversation_id` 欄
- `sub_workflow` 繼承外層 conv_id（巢狀傳遞）
- trigger_dispatcher / resume_worker 維持 None（無 chat context）

### Added — Per-user billing UI (v3.8-P2, PR #225)
- `services/agent/app/api/admin_billing.py`：
  - `/users` — 當月所有 user 總覽（join users + workspaces，計算 cost / tokens / calls / conversations）
  - `/users/{id}` — 單一 user 詳情（by_feature / top_conversations / daily timeseries）
  - `/users.csv` — 匯出 CSV
- 三層 routing（agent mount + gateway proxy GET-only）；admin role gate
- 前端 `BillingView.vue`：月份 select + summary card + table + 點 row 抽屜詳情
- DashboardLayout nav SIcon `file-text`

### Added — Multi-judge averaging (v3.8-P3, PR #226)
- `rag_eval.py`：
  - 新 `--judge-models` 參數（plural，多個 judge）；保留 `--judge-model` 相容
  - Spec format: `model@base@key`（@ 分隔可缺、預設 fallback）
  - `run_mode()` 收 `judge_cfgs: list[dict]`，每 query 對每個 judge 評一次
- Output：
  - `judge_consensus` = mean of per-judge means
  - `judge_stdev` = stdev of means（分歧度）
  - Per-judge breakdown table
- 文件補解讀指引（stdev < 0.5 一致 / 0.5-1.0 中度 / > 1.0 高度分歧）

### Added — Query plan analyzer (v3.8-P4, PR #227)
- alembic `0014_slow_query_explains`：JSONB plan + sql_hash dedup
- `core/slow_query.py` 擴展：
  - 偵測 slow → `asyncio.create_task` 跑 `_capture_explain`（不阻塞原 query）
  - SELECT 用 `EXPLAIN (ANALYZE, FORMAT JSON)`；非 SELECT 只用 `EXPLAIN (FORMAT JSON)` 避免 INSERT/UPDATE/DELETE 被重執行
  - 含 bind params 的 query skip（不能安全 inline）
  - 5 min dedup by sql_hash 避免風暴
  - EXPLAIN 自己加 guard 防遞迴
- `/admin/slow-queries` API：
  - list（24h, by duration）
  - `{id}` 拿完整 plan
  - `top-by-hash` aggregate（occurrences / max / avg）
- 三層 routing（agent mount + gateway proxy）
- 前端 `SlowQueriesView.vue`：tab 切換 + 抽屜 pre-print plan
- SIcon `database`

### Breaking Changes
- ⚠️ **alembic 0014** auto-migrate
- ⚠️ Slow query 多一個 async task per slow event（資源 overhead 微小）

### v3.x 系列收尾
v3.7 列的 4 條 known limitations 全收完：
- ✅ workflow executor conv_id（v3.8-P1）
- ✅ Per-user billing UI（v3.8-P2）
- ✅ Multi-judge averaging（v3.8-P3）
- ✅ Query plan analyzer（v3.8-P4）

**下一個 milestone = v4.0 大改**（拔 LegacyURLBridge、bootstrap_ddl、distributed task queue、multi-region）。

### Migration（從 v3.7 升 v3.8）
1. **DB**：alembic 自動跑 `0014`（1 CREATE TABLE）
2. **Workflow**：既有 workflow run 行為不變；想對 chat-embedded workflow 歸帳 conv，前端傳 `body.conversation_id`
3. **Billing UI**：admin 進 `/admin/billing` 看每位 user 當月用量；CSV button 匯出
4. **rag_eval**：`--judge-models gpt-4o-mini claude-3-haiku@https://api.anthropic.com/v1@...` 多 judge
5. **Slow query**：v3.7 已有 listener，v3.8 自動加 EXPLAIN capture；不想要可設 `SLOW_QUERY_CAPTURE_EXPLAIN=false`

### PR refs
#223（roadmap）/ #224（workflow conv_id）/ #225（billing UI）/ #226（multi-judge）/ #227（query plan）

---

## [3.7.0] — 2026-05-18

> **Cost attribution + LLM-as-judge + Slow query trace** milestone — 從 quota 拓展到 per-conversation cost、評估從 hit@5 升級到 LLM 評分、observability 補慢 query 追蹤。

### Highlights
- 💰 **Per-conversation cost** — `model_usage_logs` 加 `conversation_id` / `message_id`，前端 chat header 顯示 💰 $X · 🔤 N tokens
- 🏷️ **Feature labelling** — 每筆 usage log 標 `feature`（chat / workflow / image / stt / tts / rerank），新 Grafana dashboard 分流
- 🧑‍⚖️ **LLM-as-judge eval** — `rag_eval.py --judge-model` 啟用 0-5 LLM 評分，每 query top-5 送 judge
- 🐢 **Slow query trace** — SQLAlchemy event listener，>500ms 寫 log + OTel span tag

### Added — Conversation cost attribution (v3.7-P1, PR #218)
- alembic `0012_conversation_cost`：`model_usage_logs.conversation_id` + `message_id` + partial index
- `UsageRecord` / `record_usage` / `meter_llm_call` / `meter_media_call` 全鏈加 conversation_id + message_id（keyword-only, default None）
- 3 chat endpoints 接 body.conversation_id（fallback session_id 驗 UUID；public chat 無 fallback）
- 新 API `GET /workspace/{ws}/conversations/{id}/cost` → total + by_message[]
- 三層 routing（agent mount + legacy_bridge + gateway proxy）
- 前端 `ConversationCostBadge.vue` 掛在 ApplicationChatView header → lazy load 顯示

### Added — Cost-by-feature dashboard (v3.7-P2, PR #219)
- alembic `0013_usage_feature`：`model_usage_logs.feature VARCHAR(16)` + partial index
- 7 個 metering call site 標 feature：
  - 3 chat endpoint → `chat`
  - workflow executor LLM nodes (3 處) → `workflow`
  - executor `_exec_image_generate` → `image`
  - executor `_exec_stt` → `stt`
  - executor `_exec_tts` → `tts`
  - executor `_exec_reranker` → `rerank`
- 新 Grafana dashboard `v3-cost-by-feature.json`：
  - 本月 cost by feature (barchart)
  - daily cost by feature (timeseries 30d)
  - top 20 conversations by cost (table)
  - top 20 users by cost (join users)

### Added — LLM-as-judge eval (v3.7-P3, PR #220)
- `tools/eval/rag_eval.py` 加 `--judge-model` / `--judge-base` / `--judge-key` 參數
- `llm_judge()` helper：OpenAI-compat `/chat/completions` 呼叫，prompt 含 0-5 rubric → 取 first int
- `run_mode()` 加 `judge_cfg` kwarg：每 query 收 top-5 passages 送 judge → 平均
- markdown output 多一欄 `judge_avg`（有設 --judge-model 才印）
- 失敗（network / parse error）→ skip 該 query 不污染平均
- dataset 可加 `judge_criteria` 欄位給 judge 額外 rubric（per-query rubric）
- 文件 `docs/perf/v3.3-rag-bench.md` 補 v3.7 P3 章節
- 向後相容：不設參數 → 行為不變

### Added — Slow query trace (v3.7-P4, PR #221)
- 新 `core/slow_query.py`：
  - SQLAlchemy `event.listens_for` `before_cursor_execute` / `after_cursor_execute`
  - 超過 `SLOW_QUERY_THRESHOLD_MS`（預設 500ms）→ structlog warning（含 sql preview + params + duration_ms）
  - 加 OTel span 三個 tag：`db.slow=true`、`db.duration_ms=N`、`db.statement_preview`
- lifespan 在 `init_db()` 後安裝 listener（try/except 防爆）
- compose `agent` env 加 `SLOW_QUERY_THRESHOLD_MS`
- Grafana `v3-observability-demo.json` 加 logs panel：Loki filter `slow_query` JSON → 顯示 ms + sql
- 對 sync + async engine 都適用（async engine 用 `sync_engine` 拿底層）

### Breaking Changes
- ⚠️ **alembic 0012 / 0013 auto-migrate**（2 個 ADD COLUMN）
- ⚠️ **model_usage_logs 加 2 個 index**（partial index、不影響既有寫入效能）
- ⚠️ **Slow query listener**：所有 query 多一個 event hook（微小 overhead，benchmark 顯示 < 0.1ms per query）

### Known limitations（→ v3.8）
- Per-user billing UI（→ SaaS 主題）
- Multi-judge averaging（GPT-4 + Claude + 人工）→ v3.8
- Query plan analyzer（pg_stat_statements 整合）→ v3.8
- workflow executor conversation_id 暫保持 None（v3.8）

### Migration（從 v3.6 升 v3.7）
1. **DB**：alembic 自動跑 0012 + 0013（4 個 ADD COLUMN + 2 partial index）
2. **Feature labels**：升完後新 usage logs 自動帶 feature；舊 row `feature IS NULL`，dashboard 顯示為 `unknown`
3. **Conversation cost**：前端 ApplicationChatView 自動顯示；無需配置
4. **LLM-as-judge**：opt-in，跑 eval 時加 `--judge-model gpt-4o-mini --judge-key $OPENAI_KEY`
5. **Slow query**：自動啟用、預設 500ms threshold；`SLOW_QUERY_THRESHOLD_MS=300` 可調更敏感
6. **Grafana**：載入新 dashboard `v3-cost-by-feature`、刷新 `v3-observability-demo` 即看到 slow query panel

### PR refs
#217（roadmap）/ #218（conv cost）/ #219（feature dashboard）/ #220（LLM-as-judge）/ #221（slow query）

---

## [3.6.0] — 2026-05-18

> **Async resilience** milestone — 強化非同步任務的可靠性、idempotency、graceful shutdown。

### Highlights
- 📬 **Webhook outbox + retry** — 失敗自動 exp backoff (1m/5m/30m/2h/12h)，5 次後 DLQ；admin 可手動 retry
- 💓 **Task heartbeats** — 5 個背景 worker 加 heartbeat upsert + admin UI + Grafana freshness panel
- 🔑 **Idempotency-Key middleware** — POST + header → 24h 內 cache JSON response
- 🛑 **Graceful shutdown** — SIGTERM 等 in-flight workflow done 才退 + 4 場景 DR drill 文件

### Added — Webhook outbox (v3.6-P1, PR #212)
- alembic `0009_webhook_outbox`：表 (status pending/in_flight/delivered/failed + attempts + next_retry_at + last_error + source_type/id)
- `core/webhook_outbox.py`：
  - `enqueue_webhook()` — caller insert row instead of httpx direct
  - `webhook_dispatcher_loop` — 30s 一輪、`FOR UPDATE SKIP LOCKED` claim、單輪上限 50
  - Backoff: `[60, 300, 1800, 7200, 43200]`（1m/5m/30m/2h/12h），5 次後 `status='failed'` (DLQ)
- `quota_alert_worker`：webhook / slack 改走 outbox，**email 保留 SMTP 直送**（v3.4-P2 邏輯）
- `_dispatch` 簽名加 `session` 參數
- `/admin/webhook-outbox` API：list + retry button（跨 ws admin only）
- 三層 routing：agent mount + gateway proxy（仿 `_make_admin_quotas_router` pattern）
- 前端 `WebhookOutboxView.vue`：status filter / retry button / 展開 error / SIcon `send`

### Added — Task heartbeats (v3.6-P2, PR #213)
- alembic `0010_task_heartbeats`：表 (worker_name PK + pid + host + started_at + last_beat + in_flight)
- `core/heartbeat.py`：`beat()` + `safe_beat()` helper（module-scoped `_started` dict 紀錄首次心跳）
- 5 worker loop 開頭加 `safe_beat`：
  - `trigger_worker` / `trigger_dispatcher` / `resume_worker` / `quota_alert_worker` / `webhook_dispatcher`
- `/admin/heartbeats` API + 前端 `HeartbeatsView`（30s auto-refresh）
- Pill / Grafana 三色 threshold：
  - < 120s 綠（健康）
  - < 300s 黃（延遲）
  - >= 300s 紅（失聯）
- Grafana `v3-workers.json` dashboard（PG datasource + cell color-background）
- DashboardLayout nav SIcon `loader`

### Added — Idempotency middleware (v3.6-P3, PR #214)
- alembic `0011_idempotency_keys`：表 (PK = key + endpoint, default `expires_at = now() + 24h`)
- `middleware/idempotency.py`：
  - 只攔 POST + `Idempotency-Key` header
  - SSE / streaming endpoint 跳過（path 含 `chat`/`stream`/`sse`/`run` 或 `Accept: text/event-stream`）
  - 第一次：收集 body chunks（starlette `BaseHTTPMiddleware` pattern）→ INSERT `ON CONFLICT DO NOTHING`（並發安全）
  - 第二次：直接回 cached `JSONResponse` + header `Idempotency-Replayed: true`
  - 5xx response 不快取（client 應重試）
  - 非 JSON response 不快取
- Middleware order：LegacyURLBridge（外）→ **Idempotency** → GatewayHeaders → TenantContext → CORS（內）
- 文件 `docs/dev/idempotency.md`（含 curl 範例 + cleanup SQL cron）

### Added — Graceful shutdown + DR drill (v3.6-P4, PR #215)
- agent service lifespan finally block：
  - 標 shutdown 後，等 `event_trigger_runs WHERE status='running'` count 歸 0 或 30s timeout
  - log `graceful_shutdown_waiting` 每 2s / `graceful_shutdown_no_inflight` / `graceful_shutdown_timeout_30s`
  - 接著 cancel 5 個 worker（既有 pattern）
- compose `agent` service `stop_grace_period: 60s`
- 新文件 `docs/deploy/dr-drill.md` — 4 場景演練 runbook：

| 場景 | RTO | RPO |
|---|---|---|
| K8s rolling update | < 60s | 0 |
| PG primary failover | 1-2 min | < 30s |
| Redis restart | < 30s | counter reset |
| Backup full restore | 10-30 min | 24h |

### Breaking Changes
- ⚠️ **Quota alert webhook 改走 outbox**：對外 webhook 不再 sync 送、有 30s 延遲。Slack 失敗會自動重試（之前直接 log 不重試）
- ⚠️ **alembic 0009 / 0010 / 0011** auto-migrate（3 個 CREATE TABLE）
- ⚠️ **agent container `stop_grace_period: 60s`**：滾動更新會比之前慢 ~30-60s（換取 in-flight workflow 保護）

### Known limitations（→ v3.7）
- Idempotency cleanup worker（目前只能手動 SQL cron）
- Webhook signing / HMAC（v3.7）
- Webhook outbox retention cleanup（delivered > 7d）
- Multi-region active-active → v4.0
- 在 SSE / streaming endpoint replay response（技術上需大改，v4.x）

### Migration（從 v3.5 升 v3.6）
1. **DB**：alembic 自動跑 0009 / 0010 / 0011（3 個 CREATE TABLE，全 IF NOT EXISTS）
2. **Webhook alert**：升完後對外 webhook 變 async 走 outbox；admin 進 `/admin/webhook-outbox` 看 status
3. **Heartbeat**：5 個 worker 啟動後 30s 內 upsert；admin `/admin/heartbeats` + Grafana `v3-workers` dashboard 可看
4. **Idempotency**：client 對 POST 加 `Idempotency-Key: <uuid>` header → 自動 dedup；不加 header 行為不變
5. **Graceful shutdown**：K8s rolling update 預期慢 30-60s（換取 workflow 保護）；不滿意可設 `stop_grace_period: 5s` 回舊行為
6. **DR drill**：建議每季跑一次 `docs/deploy/dr-drill.md` 4 場景

### PR refs
#211（roadmap）/ #212（webhook outbox）/ #213（heartbeats）/ #214（idempotency）/ #215（graceful shutdown）

---

## [3.5.0] — 2026-05-18

> **Workflow ecosystem expansion** milestone — 補齊 workflow 還缺的 nodes + run observability。
> 重點：human approval flow + sub workflow 巢狀 + run step persistence + 完整 admin viewer。

### Highlights
- 🧑‍⚖️ **human_approval node** — workflow 跑到此 node 暫停、admin 點同意才續跑
- 🔁 **sub_workflow node** — 巢狀呼叫另一個 application 的 workflow（防遞迴 depth>3）
- 📜 **Run step persistence** — 每個 node 的 input/output/status 寫進 DB
- 🖥️ **Run history UI** — admin step-by-step viewer（含 retry / paused 視覺化）

### Pre-roadmap discovery
v3.5 規劃時以為要做 6 個新 node，盤點後發現 4 個已在 codebase：
- `http_request` / `condition`+`switch` / `loop`+`map` / `wait`+`schedule` 全有
- `WorkflowExecutor(workflow_manager="retry")` 已支援 3 次重試 + 指數退避

實際只做 2 個新 node + step persistence + UI。

### Added — Run step persistence (v3.5-P1, PR #206)
- alembic `0007_workflow_run_steps`：
  ```sql
  CREATE TABLE workflow_run_steps (
    id, run_id, step_index, node_key, node_type, status,
    input_snapshot JSONB, output_snapshot JSONB,
    error, attempts, latency_ms, started_at, finished_at
  );
  CREATE INDEX idx_wrs_run ON (run_id, step_index);
  ```
- `WorkflowExecutor`：
  - `__init__` 加 `run_id` keyword-only + `self._step_idx`
  - `_record_step()` helper：4KB JSON truncate + 寫失敗只 log + jsonb CAST
  - dispatch wrapper 三狀態：ok / error / retry（retry path 獨立寫，避免雙寫）
- `trigger_dispatcher`：`WorkflowExecutor(run_id=rec["run_id"])`
- 新 API：
  - `GET /workspace/{ws}/applications/{app}/runs` — list (含 tokens_used + cost_usd + trigger_name)
  - `GET /workspace/{ws}/applications/{app}/runs/{run_id}/steps` — step list（含越權檢查）

### Added — human_approval node + resume worker (v3.5-P2, PR #207)
- alembic `0008_workflow_approvals`：
  - `workflow_approvals` 表（status pending/approved/rejected + CHECK + GIN(status) partial index）
  - `event_trigger_runs` 加 `paused_at` / `resumed_at` / `resume_node`
- 新 `WorkflowPaused` exception
- `_exec_human_approval`：寫 pending row → raise `WorkflowPaused`
- `WorkflowExecutor` 加 `resume_from_node` kwarg：從指定 node 的下一個 node 開始
- `trigger_dispatcher`：catch `WorkflowPaused` → status='paused'、寫 `paused_at` + `resume_node`、不寫 `finished_at`
- 新背景 worker `resume_worker_loop` 每 30s：
  - 掃 `event_trigger_runs.status='paused'` 且 `workflow_approvals.status='approved'`
  - approved → 從 resume_node 之後續跑
  - rejected → 標 `status='rejected'`、不續跑
- 新 API：`/approvals` (list / approve / reject) — admin only
- 三層 routing：agent mount + legacy_bridge prefix + gateway proxy
- 前端：
  - LogicFlow `human_approval` node（紫色，icon 「人」）
  - `views/admin/ApprovalsView.vue`（status filter / pending table / approve+reject modal）
  - router + nav (`check-circle` icon)

### Added — sub_workflow node (v3.5-P3, PR #208)
- `WorkflowExecutor` 加 `depth` kwarg（>3 raise `RuntimeError`）
- 新 `_exec_sub_workflow`：載入 sub application 的 workflow、巢狀 executor (`depth+1`)、events 加 `sub.` prefix 不污染外層 stream
- 最後結果塞回外層 `context[output_variable]`
- 設計決定：
  - sub run 不寫 `workflow_run_steps`（避免污染外層 run_id；保持 trace 簡單）
  - sub metering 仍正常歸帳到 `sub_application_id`（cost 正確）
  - 跨 workspace sub_workflow 不支援
- LogicFlow FE 加 `sub_workflow` node（青色，icon 'Sub'）+ defaults + palette「組合」分組

### Added — Run history UI (v3.5-P4, PR #209)
- `api/runHistory.ts` — listRuns / listSteps
- `views/admin/RunHistoryView.vue`：
  - Application select 切換
  - 左欄：run list（status badge / tokens / cost）
  - 右欄：step timeline（icon / latency / attempts / status pill）
  - 點 step 展開 input/output snapshot（JSON pretty print，bg-neutral-50 + max-h-60 overflow）
  - 顏色：ok 綠 / error 紅 / retry 黃 / paused 紫
- router 加 `admin/run-history` (roles=['admin']) + DashboardLayout nav（SIcon `play`）

### Breaking Changes
- ⚠️ workflow LLM call 寫多一筆 `model_usage_logs`（v3.5 之前 streaming case 不寫，v3.5 改用 metering helper 寫）— 對 cost 計算更精確、無破壞
- ⚠️ alembic 0007 / 0008 auto-migrate；新表預設無資料、不影響既有 workflow

### Known limitations（→ v3.6）
- Approval email 通知（用 quota_alert worker pattern；v3.6 backlog）
- Multi-approver / 多階核（多個 admin 投票）
- Approval timeout auto-reject（時效機制）
- Run replay（同 input 重跑 button）
- Step-level retry config（不同 node 不同 retry policy）

### Migration（從 v3.4 升 v3.5）
1. **DB**：alembic 自動跑 `0007_workflow_run_steps` + `0008_workflow_approvals`（2 個 CREATE TABLE + 3 個 ADD COLUMN）
2. **Workflow**：既有 workflow 不動；新 node `human_approval` / `sub_workflow` opt-in 加入
3. **Resume worker**：lifespan 自動啟，每 30s 掃 paused run；停 worker：`docker compose restart agent`
4. **Admin UI**：新 2 個 nav 條目（approvals / run-history），admin 角色登入後可見

### PR refs
#205（roadmap）/ #206（step persistence）/ #207（human_approval）/ #208（sub_workflow）/ #209（run history UI）

---

## [3.4.0] — 2026-05-18

> **v3.3 留尾收口** milestone — 把 v3.3 known limitations 4 條全收完。
> 重點：純收尾、無新主題；v3.x 收尾紀律。

### Highlights
- 🎬 **Non-LLM workflow metering** — image-gen / STT / TTS / reranker 4 個 node 接 unit-based pricing (`meter_media_call`)
- 📧 **Email SMTP dispatch** — quota_alert email channel 從 log-only → 真送（aiosmtplib）
- 🎯 **Cross-encoder reranker** — 獨立 service container（sentence-transformers + bge-reranker-v2-m3），取代 Ollama embedding cosine fallback
- 📊 **RAG eval CI** — 10 篇 zh-TW seed corpus + 22 anchors + GH Action 每週跑 + threshold gate

### Added — Non-LLM metering (v3.4-P1, PR #200)
- alembic `0006_media_pricing`：
  - `ai_models` 加 `price_per_image_usd` / `price_per_second_usd` / `price_per_1k_chars_usd` / `price_per_call_usd`
  - `model_usage_logs` 加 `unit_type` (image/second/char/call) + `unit_count`
- `MEDIA_PRICING` seed 9 個 model：dall-e×3 / whisper-1 / tts×2 / 3 個 reranker（cohere v3 / bge / english）
- 新 `calc_media_cost(session, *, model, unit_type, unit_count) -> float` helper
- 新 `meter_media_call` async context manager（與 `meter_llm_call` 對稱：pre check_quota + post record_usage + cost auto-calc + commit）
- 4 個 workflow node 接 metering：
  - `_exec_image_generate` — `unit=image, count=n`
  - `_exec_stt` — `unit=second, count=len(audio)/4000`（32kbps 估算）
  - `_exec_tts` — `unit=char, count=len(text)`
  - `_exec_reranker` — `unit=call, count=1`
- Graceful degrade 同 v3.3-A pattern（無 session/workspace 走原邏輯）

### Added — Email SMTP dispatch (v3.4-P2, PR #201)
- 新 `services/agent/app/core/email.py`：`aiosmtplib` thin wrapper
- `quota_alert_worker` email 分支從 `log.info("...pending")` → `await send_email(...)`
- settings 加 `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM` / `SMTP_USE_TLS`
- compose agent service environment + `.env.example` 加註解範例
- `aiosmtplib==3.0.2` 加進 agent requirements
- SMTP_HOST 未設 → `send_email()` log skip + 回 False（dev 友善、不破壞既有行為）

### Added — Cross-encoder reranker (v3.4-P3, PR #202)
- 新 service `services/reranker/`（FastAPI thin wrapper）：
  - `POST /rerank` body `{query, documents, top_n}` → `{indices, scores}`
  - `sentence-transformers` + `BAAI/bge-reranker-v2-m3`（device 可設 cpu/cuda）
  - lazy load（cold start ~2 min、model ~1GB）
- compose 加 `reranker` service（profile `reranker`，預設 disabled、2G mem limit、port 8010、`reranker_hf_cache` volume 持久化）
- knowledge `core/reranker.py` 加 `cross_encoder` dispatch：
  - config: `{"type": "cross_encoder", "endpoint": "http://reranker:8000"}`
  - timeout 30s、失敗 fallback 回原順序
  - dict copy 後寫 `relevance_score`，不污染上游
- 文件 `docs/dev/reranker.md`：opt-in / API / 延遲 / 模型選擇

### Added — RAG eval CI (v3.4-P4, PR #203)
- 10 篇 zh-TW seed corpus（`tools/eval/seed_corpus/01-leave-policy.md` ~ `10-resignation.md`）— HR / policy 各約 260-310 字、4 段 H2 標題、deterministic 內容
- `tools/eval/seed_eval_kb.py` — 上 KB + poll embedding + 輸出 paragraph IDs 到 `seeded_paragraphs.json`
- `rag_eval_dataset.json` 加 `expected_corpus_anchors`（10 query × 22 anchors）— 用 `file + title_contains` pattern 標 ground truth
- `rag_eval.py` 加 `--seeded` 參數、`resolve_anchors()` 啟動時把 anchor 解析成實際 paragraph_id
- 新 GH Action `.github/workflows/rag-eval.yml`：
  - cron 每週日 02:00 UTC + workflow_dispatch
  - threshold gate：`hybrid+none` hit@5 < 0.5 → CI fail
  - 結果 append 進 `docs/perf/v3.3-rag-bench-history.md` 並 auto commit
- 新 `docs/perf/v3.3-rag-bench-history.md`（append target）

### Changed
- v3.3-A 在 4 個 non-LLM node 留的 `# TODO v3.4: separate metering` 註解改成 `# v3.4 P1: metered via meter_media_call`

### Known limitations / 留 v3.5
- Workflow ecosystem 新 nodes（http-call / branch-if / loop-foreach / human-approval / sub-workflow / delay-until）— v3.5 主題
- CI workflow caveat：admin password / endpoint paths / GH runner memory / Ollama cold start，需首次 workflow_dispatch 驗證

### Breaking Changes
- ⚠️ **non-LLM workflow node 進 quota check**：之前繞過 metering，現在會檢 workspace + user cap，超額 → 同 v3.3-A pattern
- ⚠️ **alembic 0006** auto-migrate；既有 `model_usage_logs` 列 `unit_type` / `unit_count` 為 NULL，不影響舊查詢

### Migration（從 v3.3 升 v3.4）
1. **DB**：alembic 自動跑 `0006_media_pricing` → 6 個 ADD COLUMN（全 IF NOT EXISTS）
2. **Pricing seed**：lifespan 自動 UPSERT 9 個 media model 定價；手動改過的不會被覆蓋
3. **Email alert**：設 `.env` SMTP_* → restart agent → email channel 開始真送；不設就維持 log-only
4. **Cross-encoder**：opt-in
   ```bash
   docker compose --profile reranker up -d
   # 首次 cold start ~2 min
   ```
   knowledge `/hit-test` body 傳 `{"reranker": {"type":"cross_encoder","endpoint":"http://reranker:8000"}}`
5. **RAG eval CI**：首次手動 workflow_dispatch 跑一次，確認 endpoint paths / admin pwd / runner memory 都 ok 後再讓 cron 自跑

### PR refs
#199（roadmap）/ #200（non-LLM metering）/ #201（SMTP）/ #202（cross-encoder）/ #203（RAG eval CI）

---

## [3.3.0] — 2026-05-18

> **Comprehensive deepening** mega-milestone — A + D + B + C 一次清。
> 收 v3.2 workflow metering 留尾、加 user-level quota + alert、上 OpenTelemetry + Loki、補 RAG reranker / eval harness。

### Highlights
- 🔁 **Theme A — Workflow metering** — workflow executor 4 個 LLM-based node 接 `meter_llm_call`、event_trigger_runs 顯示 tokens/cost
- 👤 **Theme D — Per-user quota + alert** — user-level cap、quota alert 規則（threshold / channel: email|slack|webhook）+ 背景 worker
- 🔭 **Theme B — Observability** — OpenTelemetry tracing (Tempo) + Loki log aggregation + trace exemplar + 三向跳轉 demo dashboard
- 🔍 **Theme C — RAG quality** — hit-test reranker 接線 + UI 3 score chip（vector/RRF/rerank）+ eval harness (hit@5 / MRR)

### Added — Theme A: Workflow metering (PR #191, #192)
- `core/workflow/executor.py`：4 個 LLM node 從 raw `AsyncOpenAI` 遷移到 `OpenAICompatProvider` (BaseProvider)
  - `_exec_llm` / `_exec_image_understand` / `_exec_parameter_extraction` / `_exec_intent`
  - 包 `meter_llm_call` async context manager（pre check_quota + post record_usage + cost auto-calc）
- 留 v3.4：`_exec_image_generate` / `_exec_stt` / `_exec_tts` / `_exec_reranker`（per-image/second pricing 模型不同）
- `WorkflowExecutor.__init__` 加 `application_id`（keyword-only, default None）
- SSE 入口接 `QuotaExceeded` → yield error event 含 `quota_exceeded:` 前綴
- `trigger_dispatcher.py` catch `QuotaExceeded` → `event_trigger_runs.status='quota_exceeded'`
- alembic `0003_trigger_run_cost`：`event_trigger_runs` 加 `tokens_used` + `cost_usd`，dispatcher finally 聚合本 run 期間的 `model_usage_logs` 寫回
- 前端 `TriggersView` 每 run row 顯示 🔤 tokens / 💰 cost chip

### Added — Theme D: Per-user quota + alert (PR #193, #194)
- alembic `0004_user_quotas`：`user_quotas` 表（PK = workspace_id + user_id）
- `check_quota(session, ws, user_id=None)` 兩層檢查（先 ws 後 user，任一超額 raise）
- `meter_llm_call` 把 user_id 傳進 check_quota
- alembic `0005_quota_alerts`：`quota_alerts` 表（scope/threshold_pct/channel/target/enabled + CHECK constraints）+ `quota_alert_fires`（PK alert_id + month，避免重發）
- 新檔 `core/quota_alert_worker.py`：每 10 min evaluate workspace + user scope，依 channel dispatch（webhook / slack / email log-only）
- 新 API：
  - `/user-quotas` GET list (含當月用量) / PUT {user_id}（require_admin）
  - `/quota-alerts` 標準 CRUD（require_admin）
- 三層 routing 全到位：agent mount + legacy_bridge prefix + gateway proxy
- 前端：
  - `views/admin/UserQuotaView.vue` — table + edit modal
  - `views/admin/QuotaAlertView.vue` — CRUD UI
  - `views/admin/UsageBar.vue` — 共用 progress bar（70%/90% 黃紅閾值）
  - DashboardLayout nav 加 2 條 admin 路徑（SIcon: `user` / `alert-circle`）

### Added — Theme B: Observability (PR #195, #196)
- 新 compose profile **`observability`**（預設 disabled）
- **OpenTelemetry tracing**：
  - `packages/python/staffkm-core/staffkm_core/observability.py` — `setup_otel()` + `instrument_fastapi()`（OTel endpoint 未設則 noop、失敗不阻 app）
  - 6 service 接 OTel auto-instrument（FastAPI / httpx / asyncpg / logging）
  - 加 `tempo:2.6.1` container（OTLP HTTP :4318、7d retention）
  - Grafana datasource `staffkm-tempo`（含 `tracesToLogsV2` → loki / `tracesToMetrics` → prometheus）
- **Log aggregation**：
  - 加 `loki:3.3.1` + `promtail:3.3.1` container
  - Promtail Docker SD 過濾 `staffkm-*` 容器、JSON pipeline 抽 level / event / trace_id label
  - Grafana datasource `staffkm-loki`（含 derived field `TraceID` → tempo）
- **Trace exemplar**：
  - Prometheus datasource 加 `uid=staffkm-prometheus` + `exemplarTraceIdDestinations`
  - 新 demo dashboard `v3-observability-demo.json` 展示三向跳轉：Logs (Loki) ↔ p95 latency exemplar (Prometheus) ↔ Service map (Tempo nodeGraph)
- 文件 `docs/dev/observability.md` — opt-in 步驟 + B3/B4 章節

### Added — Theme C: RAG quality (PR #197)
> **發現**：v3.3 規劃時以為要做 hybrid search + tsvector，盤點後發現 `core/vectorstore.py` 已實作 CJK tsvector + RRF hybrid search + 3 種 search_mode（hybrid/vector/fts），C1+C2 跳過。
- **C3 reranker 接 hit-test**：
  - `HitTestRequest` 加 `reranker` config + `rerank_top_n`
  - response 每筆加 `rrf_score` / `rerank_score`
  - `core/reranker.py` 新增 `_rerank_ollama`（雙路徑：先試 `/api/rerank`、fallback embedding cosine）
- **C4 hit-test UI 增強**：
  - `HitTestView.vue` 完整重寫（原為 placeholder）
  - segmented mode toggle (hybrid/vector/fts)
  - reranker checkbox + 展開 config form
  - 每段 3 個分數 chip：vector(藍) / rrf(紫) / rerank(橙)
- **C5 eval harness**：
  - `tools/eval/rag_eval.py` — argparse runner，hit@5 + MRR，多 mode × 多 rerank preset
  - `tools/eval/rag_eval_dataset.json` — 10 條 zh-TW HR / policy query 模板（expected_paragraph_ids 待人工標註）
  - `docs/perf/v3.3-rag-bench.md` — method + baseline placeholder

### Breaking Changes
- ⚠️ **workflow LLM call 進 quota check**：workflow 跑到 LLM node 時會檢 workspace + user cap，超額 → workflow_run.status=`quota_exceeded`
- ⚠️ **`opentelemetry-*` 依賴加進 6 service requirements**：image 體積 +~30 MB；不開 observability profile 也會裝（idle 不耗 CPU）
- ⚠️ **alembic 0003 / 0004 / 0005** auto-migrate；新表預設無資料、不影響既有 workflow

### Known limitations（→ v3.4）
- workflow `_exec_image_generate` / `_exec_stt` / `_exec_tts` / `_exec_reranker` 仍未接 metering
- email alert dispatch 只 log（未接 SMTP）
- Ollama reranker fallback 用 embedding cosine 效果有限，需換 cross-encoder
- eval dataset 的 expected_paragraph_ids 待人工標註後才能跑

### Migration（從 v3.2 升 v3.3）
1. **DB**：alembic 自動跑 `0003_trigger_run_cost` → `0004_user_quotas` → `0005_quota_alerts`，3 個 ADD COLUMN / CREATE TABLE 操作，全 IF NOT EXISTS
2. **Workflow**：升完後所有 workflow LLM call 都會檢 quota；想暫停可把對應 workspace_quotas 的 cap 設 NULL
3. **Quota alerts**：admin 進 `/admin/quota-alerts` 新增規則；worker 每 10 min 跑、達 threshold 發一次（月內不重發）
4. **Observability**：opt-in
   ```bash
   echo 'OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4318' >> .env
   docker compose --profile monitoring --profile observability up -d
   ```
5. **RAG**：hit-test 預設行為不變；想試 reranker 在 UI 開 checkbox 即可

### PR refs
- roadmap: #190
- Theme A: #191（workflow metering）/ #192（trigger run cost）
- Theme D: #193（user_quotas + alerts backend）/ #194（admin UI）
- Theme B: #195（OTel + Loki）/ #196（exemplar + demo dashboard）
- Theme C: #197（reranker + hit-test UI + eval）

---

## [3.2.0] — 2026-05-18

> **Cost / Quota governance** milestone — 把 LLM 成本與 workspace 額度真正管起來。
> 重點：production multi-tenant 出血控制。

### Highlights
- 💰 **Pricing registry** — `ai_models` 加 `price_per_1k_*_usd`，17 個主流 model seed（OpenAI / Anthropic / Google / Ollama）
- 📊 **真實 metering** — `meter_llm_call` async context manager 包 3 個 chat 入口，pre check_quota + post record_usage + cost auto-calc
- 🛡️ **Quota enforcement** — 超額自動 429 + `Retry-After`，SSE 入口 yield error event
- 🎨 **Admin Quota UI** — `/admin/quotas` 跨 workspace 列用量 + 設 cap
- 📈 **Cost dashboard 接真資料** — Grafana `v3-llm-usage` 從壞 placeholder（指向不存在的 `usage_log` 表）改成 4 panel 真實查詢

### Added — Pricing registry (v3.2-P1, PR #186)
- alembic `0002_ai_models_pricing`：加 `price_per_1k_input_usd` / `price_per_1k_output_usd`（NUMERIC(10,6)）— v3.1 baseline 之後**首個真正 migration**，驗證 alembic chain
- `services/agent/app/data/model_pricing.py`：17 個主流 model 的 USD/1k token 定價快照（2026-05）
- `services/agent/app/core/pricing_seed.py`：lifespan UPSERT，COALESCE 只補 NULL → **不覆蓋使用者手動設定的價格**
- `services/agent/app/core/usage.py`：新增 `calc_cost(session, *, model, prompt_tokens, completion_tokens) -> float` helper
- Auth `models.py` API：`ModelOut` 帶 pricing 欄位、4 處 SELECT 全部 include

### Added — LLM call metering (v3.2-P2, PR #187)
- 新檔 `services/agent/app/core/metering.py`：`meter_llm_call` async context manager
  - pre：`check_quota`（超額 raise `QuotaExceeded`）
  - yield：呼叫者跑 `provider.chat()`，邊串邊餵 `meter.record(prompt_tokens=..., completion_tokens=...)`
  - finally：`calc_cost` + `record_usage` + 獨立 session commit（避免 SSE 結束時 request session 已 close）
- 接 3 個 SSE chat 入口：
  - `/agents/applications/{id}/chat`（取代原 manual record_usage）
  - `/applications/{id}/chat`（原本沒接！）
  - `/public/applications/{id}/chat`（原本沒接！）
- 全域 exception handler：`QuotaExceeded` → 429 + `Retry-After: 86400`
- SSE 入口因 header 已 flush，改 yield error event 含 `quota_exceeded:` 前綴

### Added — Admin Quota UI + Cost dashboard (v3.2-P3, PR #188)
- **後端**：
  - 新 `/api/v1/admin/quotas` (GET list / PUT 設 cap)，跨 workspace、admin only（讀 `X-User-Roles` header）
  - `/usage/summary` 擴充 `by_day` / `by_model` aggregation
  - Gateway 手寫 admin proxy（不走 `make_proxy_router`，因為 admin 非 workspace-scoped）
- **前端**：
  - `apps/web/src/views/admin/QuotaView.vue` — table + progress bar（70% 黃 / 90% 紅）+ modal 設 cap
  - `apps/web/src/views/usage/UsageView.vue` — 4 stat card + by_day div bar chart + by_model table
  - DashboardLayout 加 nav：`/admin/quotas`（admin 限定）+ `/usage`（member）
- **Grafana**：
  - 修 `v3-llm-usage.json` 引用的壞表名 `usage_log` → `model_usage_logs`
  - 新 `datasources/postgres.yml` provisioning（uid `staffkm-postgres`）
  - compose 加 `POSTGRES_PASSWORD` 注入 grafana 容器
  - 4 個 panel：24h timeseries / top-10 workspaces / top-10 models / cap utilization gauge

### Breaking Changes
- ⚠️ **Workspace quota 預設仍 NULL（無上限）**：升級後不主動執行 quota，但所有 LLM call 都會 metering 寫 `model_usage_logs`
  - operator 想啟用 quota：admin 進 `/admin/quotas` 設各 workspace cap
  - 設了 cap 的 workspace 用滿就會 429
- ⚠️ **chat endpoint 可能回 429**：existing client 要處理 429 + `Retry-After` header（之前不會出現）

### Known limitations / 留 v3.3
- **workflow executor 沒接 metering** — `_exec_llm` 直接用 raw `AsyncOpenAI` 不走 BaseProvider；要先重構 executor 接 session_factory + 遷移到 BaseProvider，wider refactor
- `/preview/chat` 故意不接（原檔註解：「preview 不寫 usage log」）

### Migration（從 v3.1 升 v3.2）
1. **DB**：alembic 自動跑 `0002_ai_models_pricing` → 加 2 欄位、不破壞既有資料
2. **Pricing seed**：lifespan 自動 UPSERT 17 個 model 定價；手動改過的不會被覆蓋
3. **Quota**：升完後行為不變（沒人設 cap）；admin 想啟用就到 `/admin/quotas` 設
4. **Grafana**：`docker compose --profile monitoring up` 重啟 grafana 容器，新 datasource + 修好的 dashboard 自動上
5. **Frontend**：admin 看得到 `/admin/quotas` nav、所有 member 看得到 `/usage` nav

### PR refs
#185（roadmap）/ #186（pricing）/ #187（metering）/ #188（UI + dashboard）

---

## [3.1.0] — 2026-05-18

> **Technical debt cleanup** milestone — 收 v3.0 留下的 3 條尾巴。
> 重點：純收尾，無新功能。Alembic 落地 + Audit log 真實接線 + Legacy URL bridge 預設 410。

### Highlights
- 🗄️ **Alembic baseline** — 4 service（auth / agent / knowledge / chat）schema 演化改走 alembic + `pg_advisory_lock` 多 instance 安全
- 📜 **Audit log 真實接線** — 14 個寫操作埋點（applications / templates / api_keys / kb / users）
- 🌉 **LegacyURLBridge default 翻 410** — gateway proxy + frontend axios 自動注入 `X-Workspace-ID`，bridge 變 backstop only

### Added — Alembic baseline (v3.1-P1, PR #181)
- 每個 service：`alembic.ini` + `alembic/env.py` + `alembic/versions/0001_baseline.py`（no-op stamp）+ `app/utils/migrate.py`
- env.py：async URL → sync URL；online 用 `pg_advisory_lock(hashtext('staffkm_migrate_{svc}'))` 包 upgrade
- lifespan 加 `await run_alembic_upgrade()`，在 `init_db()` + bootstrap_ddl 之後
- 既有 `bootstrap_ddl.py` / `_*_BOOTSTRAP_DDL` 標 `[DEPRECATED in v3.1]`，新 schema 改動請走 `alembic revision`
- requirements 補 `psycopg2-binary==2.9.10`（alembic 需 sync driver）
- Dockerfile COPY `alembic/` + `alembic.ini`
- **integration service 跳過**：尚未接 DB

### Added — Audit log 真實接線 (v3.1-P2, PR #182)
- 新檔 `packages/python/staffkm-core/staffkm_core/audit.py`：把 `_record` 搬到 shared package、重命名 `record_audit`
- `services/agent/app/api/audit.py` 改 re-export 保留 `_record` 名稱（向後相容）
- 14 處寫操作埋點：

| Service | 檔 | 埋點數 | Actions |
|---|---|---|---|
| agent | applications.py | 3 | create / update / delete |
| agent | app_templates.py | 4 | install_from_marketplace / create / update / delete |
| agent | api_keys.py | 3 | create / revoke / toggle |
| knowledge | knowledge_bases.py | 2 | create / delete |
| auth | users.py | 2 | create / status_change |

- 失敗安全：`_safe_audit()` 包 try/except，audit 寫不進去不會中斷原 endpoint
- 敏感資料保護：api_key create detail 不含 raw key

### Changed — Legacy URL sunset phase 1 (v3.1-P3, PR #183)
- `services/gateway/app/routers/_generic_proxy.py`：`make_proxy_router` 從 `X-Workspace-ID` request header 注入 workspace_id 進 target URL
- `apps/web/src/api/index.ts`：axios request interceptor 自動帶 `X-Workspace-ID`（從 `useWorkspaceStore().currentId`）
- `services/agent/app/middleware/legacy_bridge.py`：**default `LEGACY_URL_MODE` 從 `rewrite` 翻成 `410`**
- `infra/docker-compose.yml`：加註解版 `LEGACY_URL_MODE=rewrite`（operator 想暫緩可開）

### Breaking Changes
- ⚠️ **`LEGACY_URL_MODE` 預設 `410`**：未帶 `X-Workspace-ID` header 的舊 SDK / custom client 打 `/api/v1/{prefix}` 會拿到 410 Gone（含 `Link: <new_url>; rel="successor-version"` 指路）
  - 影響：自寫 API client、curl 測試、第三方 SDK 整合
  - 升級方式：URL 改成 `/api/v1/workspace/{workspace_id}/{prefix}/...`、或在 request header 加 `X-Workspace-ID: {ws_uuid}`
  - 回滾：compose 設 `LEGACY_URL_MODE=rewrite` + restart agent
  - v4.0 預計拔除 bridge

### Migration（從 v3.0 升 v3.1）
1. **DB**：什麼都不用做。Alembic baseline 是 no-op；現有 `bootstrap_ddl` 依然跑、schema 不變。新 schema 改動才走 alembic。
2. **Audit log**：升完後執行任一寫操作 → 進 `/admin/audit-logs` 看得到 row（v3.0 是空表）
3. **舊 API client**：見上方 Breaking Changes
4. **Frontend / Gateway**：不需動作，已自動帶 workspace header
5. **監控**：升級後 1 週留意 log `legacy_url_blocked_410`，定位未遷移 caller

### PR refs
#180（roadmap）/ #181（alembic）/ #182（audit wiring）/ #183（legacy sunset）

---

## [3.0.0] — 2026-05-18

> **Production Hardening** milestone — 第一個 major release。
> 重點：把 v2.x 累積的技術債（in-process state、LegacyURLBridge、無 audit 軌跡、缺 E2E 自動化）一次清掉，
> 為長期 multi-tenant production 部署打下基礎。

### Highlights
- 🔐 **Auth hardening** — CAPTCHA 計數搬到 Redis（多 instance safe）+ OIDC schema 正規化（`oidc_sub` / `oidc_issuer`）
- 🌉 **LegacyURLBridge sunset path** — 新增 `LEGACY_URL_MODE` 環境變數（rewrite / 410 / off），預告 v3.x 拔除
- 📜 **Audit log API + UI** — `/admin/audit-logs` 可查、可篩、workspace-scoped；前端 admin 介面
- 📊 **5 個 Grafana dashboard** — traffic / endpoints / resource / LLM usage / celery
- 🎭 **Playwright E2E** — 5 個 P0 critical-path spec（login / captcha / app / kb / widget）

### Added — Auth hardening (v3.0-P1, PR #176)
- `services/auth`：
  - `_fail_count` / `_fail_record` / `_fail_clear` 改 async + Redis backed
    （key: `staffkm:auth:fail:{ip}:{username.lower()}`，TTL 10 min，原子 INCR+EXPIRE pipeline）
  - Redis 不可用時 fallback in-process dict（不阻塞登入）
  - `User` model 加 `oidc_sub: String(256, index=True)` + `oidc_issuer: String(256)`
  - `_AUTH_BOOTSTRAP_DDL` 加 3 條 `ALTER TABLE ADD COLUMN IF NOT EXISTS` + 1 條 backfill
    （`UPDATE users SET oidc_sub = SUBSTRING(ldap_dn FROM 6) WHERE ldap_dn LIKE 'oidc:%'`）
  - OIDC callback：優先 `oidc_sub` lookup、fallback email；email-only 老帳號首次 SSO 自動補 `oidc_sub`
- `services/agent` middleware `LegacyURLBridge`：
  - 新環境變數 `LEGACY_URL_MODE`
    - `rewrite`（預設，v2.x 相容）— `/api/v1/{prefix}/...` → `/api/v1/workspace/{ws}/{prefix}/...`
    - `410` — 回 `410 Gone` + `Link: <new_url>; rel="successor-version"`
    - `off` — bypass
  - 預告：v3.x 之後 default 改 `410`、v4.x 完全移除

### Added — Audit log + Grafana (v3.0-P2, PR #177)
- `services/agent/app/api/audit.py`（新）：
  - `GET /api/v1/workspace/{ws}/admin/audit-logs?actor=&action=&resource=&since=&page=&page_size=`
  - 沿用既有 partitioned `audit_logs` table，SELECT alias 補相容欄位名
  - workspace-scoped where：`(workspace_id = :ws OR workspace_id IS NULL)`
  - `_record()` helper 給其他 endpoint 寫入（INSERT 用 `CAST(NULLIF(:ip, '') AS inet)`）
- DDL：`audit_logs` ALTER 加 `workspace_id` / `actor_username` / `entity_label` + 2 index
- Gateway proxy：`/api/v1/admin/audit-logs` → agent service
- Legacy bridge `_LEGACY_PREFIXES` 加 `/api/v1/admin/audit-logs`
- 前端 `apps/web/src/views/admin/AuditLogsView.vue`：
  - Action / Entity filter chips、分頁、JSON detail expandable
  - action badge 顏色（create / delete / update / login）
- Grafana dashboards（`infra/monitoring/grafana/dashboards/v3-*.json`）：
  - `v3-traffic` — 5xx rate / RPS / latency p50/p95/p99
  - `v3-endpoints` — top endpoints by request / error
  - `v3-resource` — CPU / RSS / open FD（用 `process_*` 系列）
  - `v3-llm-usage` — token 用量（PG datasource）
  - `v3-celery` — 任務 queue lag（celery-exporter）

### Added — Playwright E2E (v3.0-P3, PR #178)
- `apps/e2e/`（新 package `@staffkm/e2e`，`@playwright/test ^1.49.0`）：
  - `playwright.config.ts` — workers=1（CAPTCHA 隔離）、`trace: retain-on-failure`、baseURL from `STAFFKM_BASE_URL`
  - `fixtures/admin.ts` — `loginAsAdmin(page)` helper
  - 5 個 P0 spec：
    - `01-login` — admin 登入 + 錯密碼出 error
    - `02-captcha` — 4 次失敗觸發 `captcha_required`（用 `e2e_${timestamp}` 隔離）
    - `03-app-crud` — `/applications` render + `?tour=templates` 自動開模板畫廊
    - `04-knowledge` — KB 列表 + API 建 KB → 列表看到
    - `05-widget` — `/widget.js` + `/widget-demo.html` 載入無 JS 錯誤
- `README.md`：env 變數、CI 整合骨架、加新 spec 慣例、known gotchas

### Changed
- Auth service lifespan 加跑 `_run_auth_bootstrap_ddl()`（OIDC 欄位 idempotent migration）
- `services/agent/app/main.py` `include_router(audit.router)` 掛 `/admin/audit-logs`
- Gateway `_generic_proxy.py` 加 `audit_logs_router`

### Breaking Changes（forward-looking）
- ⚠️ **`LEGACY_URL_MODE` 環境變數**：本版仍預設 `rewrite`，**v3.x 之後將改 `410`、v4.0 移除 bridge**
  - 影響：所有直接打 `/api/v1/{prefix}/...`（沒帶 workspace）的 client（含 gateway proxy / 前端）需在 v3.x 內逐步改打 workspace-scoped URL
  - 建議：開發環境提早設 `LEGACY_URL_MODE=410` 找出殘留 caller
- ⚠️ **OIDC user schema**：舊 `users.ldap_dn = 'oidc:{sub}'` 的記錄在啟動時會自動 backfill 到 `oidc_sub`；新 SSO 不再寫 `ldap_dn`
  - 上線後 `ldap_dn` 對 OIDC 帳號不再更新；reporting 請改讀 `oidc_sub` / `oidc_issuer`

### Migration（從 v2.5 升 v3.0）
1. **DB**：什麼都不用做。Auth + Agent service 啟動時跑 idempotent DDL，自動補 `users.oidc_sub` / `audit_logs.workspace_id` 等欄位 + backfill。
2. **Redis**：CAPTCHA 計數現在會用 DB 3；確保 `REDIS_PASSWORD` 設好（compose 已內建）。Redis 掛掉會 fallback in-process，不阻塞登入。
3. **Frontend**：admin 角色登入後左側 nav 多 `/admin/audit-logs`，無需重設權限。
4. **E2E**：`cd apps/e2e && pnpm install && pnpm exec playwright install chromium && pnpm test`。
5. **Grafana**：5 個 dashboard JSON 放在 `infra/monitoring/grafana/dashboards/v3-*.json`，provisioning 已 mount，restart Grafana 即看到。

### PR refs
#175（roadmap）/ #176（auth hardening）/ #177（audit + dashboards）/ #178（Playwright E2E）

---

## [2.5.0] — 2026-05-17

> **Developer partners** milestone — CLAUDE.md / API ref / template marketplace。
> 重點：把 staffKM 變成可以「跟其他 dev / AI 助理協作」+ 「生態擴散」的平台。
> v2.x roadmap 完成。

### Highlights
- 🧠 **CLAUDE.md** — repo-level project memory，凝結 Sprint 14-25 設計決策 + 踩雷集 + 風格慣例
- 📘 **API reference 完整 doc** — 7000 字、12 個資源組、SSE 範例、SDK
- 🌍 **Template marketplace** — 跨 workspace 分享模板 + 安裝計數 + install button

### Added — CLAUDE.md (v2.5-A)
新檔 `CLAUDE.md`（repo root）：
- 10 個重要原則（compose / Auth / Design system / Icon / Nav / routing 三層 / SQL CAST / DDL / perf 等）
- 常用指令 + Repo 結構地圖
- **8 條踩雷集**（不要再踩）
- 命名 / commit / PR 風格
- 重要 PR / Tag 對照表
- 跟使用者溝通方式 + 不要做的事

下次任何 Claude session 進這個 repo 就有完整上下文，不必重新摸索。

### Added — API reference (v2.5-B)
`docs/dev/api-reference.md` — 7000 字：
- 3 種認證方式（JWT / API Key / 公開）
- 12 個資源組 endpoint 全表（applications / kbs / docs / chat / templates / mcp / triggers / memories / usage / projects / public / app-templates）
- 統一回應格式 + SSE streaming JS / Python SDK 範例
- Rate limit / OpenAPI / Webhook / 變更日誌

### Added — Template marketplace (v2.5-C)
- DDL：`workspace_app_templates` + `is_public` + `install_count` cols
- 新 endpoints：
  - `GET /api/v1/app-templates/marketplace` — 跨 workspace 列出 public 模板（排 install_count DESC）
  - `POST /api/v1/app-templates/marketplace/{id}/install` — 複製到自己 workspace + install_count++
- TemplateCreate / Update / Out 加 `is_public` + `install_count`
- 前端 api 加 `listMarketplace()` / `installFromMarketplace()`

### v2.x roadmap 完成

| Tag | 主題 | 範圍 |
|---|---|---|
| v2.0 | GA | 105+ PRs，5 milestone |
| v2.1 | Functional parity | MaxKB 缺口 5/5 + Orphan 5 模組 + Design system v2 |
| v2.2 | Production-ready | metrics + TLS + backup |
| v2.3 | Demo polish | onboarding + citation chip |
| v2.4 | B2B | widget + SSO + user docs |
| v2.5 | Dev partners | CLAUDE.md + API ref + marketplace |

### PR refs
#173

---

## [2.4.0] — 2026-05-17

> **B2B enablement** milestone — embed widget + SSO + user docs。
> 重點：把 staffKM 變成可以「放心嵌入 / 接客戶 SSO / 給最終使用者看手冊」的元件。

### Highlights
- 🪟 **Embeddable widget** — 一行 `<script>` 嵌任何網站，6 KB vanilla JS
- 🔐 **OIDC SSO** — Google / Microsoft AD / Okta / Azure AD；最小 lift（無 DB schema 改）
- 📖 **8 篇 user-guide** — first-login / chat / KB / app / project / web-sync / embed / admin + FAQ

### Added — Embeddable Widget (v2.4-A)
- `apps/web/public/widget.js` — 6 KB vanilla JS、無依賴
  - data-app-id / data-host / data-position / data-color / data-label
  - 公開 API：`staffKM.open() / close() / toggle()`
  - Lazy mount iframe + ESC / 點空白關 + RWD
- `apps/web/public/widget-demo.html` — 互動測試頁
- `PublicChatView`：`?embed=1` → 精簡 chrome（小 header / 隱藏 Powered by chip）
- nginx + Caddy：`/widget.js` / `/widget-demo.html` / `/share/*` 允許 cross-origin iframe
  - `X-Frame-Options` 拿掉，改 `CSP frame-ancestors: *`

### Added — OIDC SSO (v2.4-B)
- `services/auth/app/api/oidc.py`：
  - `GET /info` — 前端探 SSO 啟用 + 顯示名
  - `GET /login` — redirect IdP authorize（state cookie + JWT-signed nonce 防 CSRF）
  - `GET /callback` — code → token → userinfo → upsert User → 簽 staffKM JWT → redirect 帶 `#access_token`
- 6 個新 `OIDC_*` config vars（.env.production.example 完整範例）
- 標準 OIDC discovery（抓 `/.well-known/openid-configuration`）
- Match by email；新 user auto-create role=`user`（`OIDC_DEFAULT_ROLE`）
- 借用 `user.ldap_dn` 欄存 `oidc:{sub}`（避免 DB schema migration）
- Gateway PUBLIC_PATHS 加 3 個 oidc 端點
- Frontend：
  - `api/auth.ts`: oidcInfo() / oidcLoginUrl()
  - LoginView mount 時讀 `#access_token` hash（callback redirect）→ 直接登入
  - 「使用 SSO 登入」按鈕（OIDC_ENABLED=true 才出現）

### Added — User docs (v2.4-C)
8 篇繁中 markdown（5000+ 字）：

| 檔 | 對象 | 內容 |
|---|---|---|
| README | index | 章節對照 + 一句話介紹 |
| 01-first-login | 新人 | 登入 / 導覽 / locale / theme |
| 02-chat | 使用者 | 對話 / citation chip / artifact 展開 / Project scope |
| 03-knowledge-base | 使用者 | 建 KB / 上傳 / 切片 / 命中測試 |
| 04-create-app | 建立者 | 模板 / 空白 / Workflow / 存模板 / 分享 / API |
| 05-projects | 進階 | Project 概念 / 加資源 / 切換 / 管理 |
| 06-web-sync | 進階 | 3 種模式（單 URL / 多 URL / sitemap）+ upsert |
| 07-embed-widget | 整合 | snippet + 全部選項 + API + 安全 + demo |
| 08-admin | admin | users / models / usage quota / 進階模組 / 監控 |
| 99-faq | 全 | 13 個常見問題 |

### Configuration

```env
# .env.production 加（OIDC 啟用範例）
OIDC_ENABLED=true
OIDC_DISPLAY_NAME=Google
OIDC_ISSUER=https://accounts.google.com
OIDC_CLIENT_ID=...apps.googleusercontent.com
OIDC_CLIENT_SECRET=GOCSPX-...
OIDC_REDIRECT_URI=https://staffkm.example.com/api/v1/auth/oidc/callback
OIDC_SCOPES=openid email profile
OIDC_DEFAULT_ROLE=user
```

### PR refs
#171 (all 3 in one PR)

---

## [2.3.0] — 2026-05-17

> **Demo polish** milestone — onboarding wizard + citation chip UI。
> 重點：first-run 體驗、chat 引用視覺升級。Demo-friendly。

### Highlights
- 👋 **Onboarding wizard** — first-run 3 步驟導覽（welcome / pick path / KB hint），skip 隨時可
- 💬 **Citation chip + hover preview** — 從原本 list 升級為 inline brand chip + 深色 popover 顯示內容片段

### Added — Onboarding (PR #169)
- `components/onboarding/OnboardingWizard.vue` — 3 步驟、進度條、ESC/skip 友好
- 兩條路徑：
  - 「✨ 從模板」→ `/applications?tour=templates` → 自動開模板畫廊
  - 「⚡ 空白」→ `/applications?tour=create` → 自動開建立 dialog
- localStorage `staffkm.onboarding.done` 不重複跑
- DashboardLayout mount + 只在 auth.user 存在時自動跑
- `defineExpose({ open() })` 給 settings menu 「重看導覽」

### Changed — Citation UI (PR #169)
- ChatView 助理訊息引用區從 border-left `<ul>` 升為 inline `<div>` chip group
- Chip 樣式：`bg-brand-50/60` + 編號圓圈 + doc_name truncate + 相符度
- Hover popover：深色背景 (`bg-neutral-900`) + 內容 `line-clamp-6` + 三角箭頭
- Click 行為不變 — 仍打開 ArtifactPane 看完整內容

### PR refs
#169

---

## [2.2.0] — 2026-05-17

> **Production-ready** milestone — 3 個 PR 把 dev compose 推向「能上 production」。
> Foundation for B2B 客戶部署 + 雲端 multi-tenant SaaS deployment。

### Highlights
- ✅ **All 6 services 都 expose `/metrics`** — gateway 早有，補上 agent/knowledge/chat/auth/integration
- 🔒 **Production overlay + Caddy auto-TLS** — `--prod` 一鍵切換 dev / prod；Let's Encrypt + HTTP/3 + 完整 security headers
- 💾 **完整備份 / 還原 SOP** — PG + MinIO daily snapshot + DR drill 季度節奏

### Added — Observability (v2.2-A, PR #165)
- `prometheus-fastapi-instrumentator` 加到 5 個 service requirements
- 各 main.py 加 `Instrumentator().instrument(app).expose(app, endpoint="/metrics")`
- 6/6 service 都有 `/metrics`；prometheus profile 啟動後 5/7 targets up（postgres/redis 之後加 exporter）

### Added — Production deploy (v2.2-B, PR #166)
- `infra/docker-compose.production.yml` overlay：
  - DB/Redis/MinIO 收斂不對外
  - nginx → **Caddy 2.8**（auto-TLS + HTTP/3 QUIC）
  - 全部 `restart: always` + memory limits
  - monitoring profile 預設啟動
- `infra/caddy/Caddyfile`：
  - Let's Encrypt 自動證書（90 天續訂）
  - SSE-friendly：`flush_interval=-1` + `read_timeout 600s`
  - 全套 security headers (HSTS / XFO / CSP / Permissions-Policy)
  - Grafana `/grafana/*` basic-auth 二層保護
  - `www.{$DOMAIN}` → 主 domain redirect
- `.env.production.example`：完整 secrets 模板
- `tools/scripts/safe-redeploy.sh --prod` flag：一行切 dev / prod
- `docs/deploy/production-deploy.md`：完整 runbook（前置 / init / 維運 / TLS / secret / DR / FAQ）

### Added — Backup & Restore (v2.2-C, PR #167)
- `tools/backup/backup-postgres.sh` — daily 02:00、`pg_dump --format=custom -Z 9`、保留 14 daily + 8 weekly、可推 S3
- `tools/backup/backup-minio.sh` — daily 02:15、`mc mirror --remove`、保留 14 份
- `tools/backup/restore-postgres.sh` — 互動式選 dump、DROP+CREATE、平行 jobs=4、verify table count
- `tools/backup/restore-minio.sh` — 互動式 mirror（無 --remove 防誤刪）
- `tools/backup/crontab.example` — daily cron + hourly stale-check（>26h 沒備就 ALERT）
- `docs/deploy/backup-restore.md` — TL;DR 一次性設定 + 3 個還原場景（誤刪 / 整台重灌 / 選擇性 table）+ DR drill SOP（季度）+ checklist

### Changed
- `safe-redeploy.sh` 加 `--prod` 旗標，自動切到 `.env.production` + production overlay

### 上 production 流程

```bash
# 一次性
cp .env.production.example .env.production
vi .env.production   # 填 PUBLIC_DOMAIN / ADMIN_EMAIL / secrets
sudo crontab -e      # 貼 tools/backup/crontab.example
sudo mkdir -p /var/lib/staffkm/backups/{postgres,minio}
sudo chown -R 999:999 /var/lib/staffkm/backups/postgres

# 啟動
./tools/scripts/safe-redeploy.sh --prod --all
# 等 1-3 分鐘 Caddy 拿 LE 證書，DNS 必須先指好

# 驗證
curl -I https://staffkm.example.com   # HTTP/2 200
```

### Migration

無 breaking。若已上 v2.1，照以下步驟升 v2.2：
1. `git pull` 最新 main
2. （已有 prod 環境）`./tools/scripts/safe-redeploy.sh --prod --all`
3. （首次上 prod）按上方流程

### PR refs
#165 (metrics) → #166 (prod compose) → #167 (backup)

---

## [2.1.0] — 2026-05-17

> 「GA 後第一個產品輪」— 20 個 PR、6 個 Sprint（14-20）、一天密集迭代。
> 重點：對標 MaxKB 5 缺口全關 + 5 個 orphan endpoint 模組曝光 + Design system v2 +
> Auth 強化 + Perf 三連跳 + i18n 三語系。

### Highlights
- **MaxKB-parity 5 缺口全關**：模板中心 + Web KB + ArtifactPane + Project 抽象 + 簡易建立
- **5 個 orphan endpoint 模組曝光**：MCP / Triggers / Workflow Versions / Usage Quota / Memory / Task Revoke（CRUD 真.通，含 backend routing 三層修補）
- **Design system v2 全面落地**：dark mode 100% token-flip、SIcon 44 names、ui-kit 34 元件、Storybook gallery
- **Auth 強化**：CAPTCHA 防暴力 + 401 interceptor 並發去重 + `?next=` 導回
- **Perf 三連跳**：ChatLayout **1022→9 KB** (-99%) / md-vendor **1009→200 KB** (-80%) / WorkflowEditor **66→33 KB** (-50%)
- **i18n 三語系**：繁中 / 簡中 / 英文

### Added — MaxKB-parity

- 📦 **Application 模板中心 + 6 種子模板**（#139）— 內部問答 / 客服 FAQ / 合約審閱 / SQL 助手 / 內訓教練 / 文件翻譯
- 🎮 **「立即試用」preview chat**（#145）— `/applications/preview/chat` 端點，無持久化、不計 usage
- 🌐 **Web KB 同步**（#137 早 + #141 follow-up + **#159 sitemap.xml**）— 單 URL / 多 URL 批次 / sitemap.xml recursive 一層
- 🗂 **Project 抽象 UX 全鏈**（#144 + **#158 chat scope binding**）— picker 上 DashboardLayout / `/projects` 管理頁 / 卡片 attach button / active Project KB 自動進 RAG
- 📝 **Workspace 自訂模板庫**（#157）— App 卡片「存模板」、gallery 合併 built-in + workspace
- ✨ **ArtifactPane**（#140）— marked + highlight.js + 複製 + ESC + 訊息一鍵展開

### Added — Orphan endpoints 5 模組

- 🔗 **MCP Servers Store UI**（#148）— 7 endpoints（CRUD + refresh + tools 列表 + call tool）
- 🔄 **Triggers UI**（#151）— 5 endpoints + 3 種 kind chip（interval/cron/webhook）+ runs drawer
- 📂 **Workflow Versions panel**（#154）— 3 endpoints + 右側 drawer + 「節點版本」按鈕（與既有「應用版本」並列）
- ✕ **Task Revoke**（#154）— admin 在卡住的 doc 上看到取消按鈕
- 💰 **Usage Quota UI**（#153 修 routing）— 既有 view 補上 quota 設定（端點之前 404）
- 🧠 **Memory UI**（#160）— scope filter（全部/我的/應用/團隊）+ 關鍵字搜尋 + importance slider

### Added — Design system v2

- 🎨 **SIcon 元件**（早 + 多 sprint follow-up）— 44 個 lucide-style icons + currentColor + spin
- 📐 **Typography utility classes** — `.text-h1/h2/.../body/.../caption` 全域
- 🖼 **SEmpty 4 種插圖** — box/search/doc/plus
- 📚 **Storybook Gallery**（早）— 34 元件一頁掃完 + 44 icon 預覽

### Added — Auth

- 🛡️ **CAPTCHA 登入**（#161）— 連 3 次失敗強制要求數學 CAPTCHA（10 分鐘窗口，per-IP per-username）
- 🔁 **401 interceptor 強化**（#156）— 並發 401 共用同一個 refresh、防遞迴、`?next=` 帶回原路徑

### Added — i18n

- 🇨🇳 **簡中 (zh-CN)** locale（#160）— pickInitialLocale 偵測 `zh-cn` / `zh-hans` / `zh-sg`

### Changed — UX / Design system

- **Nav 重構**（#143 + **#150**）— `/skills` `/tools` `/data-sources` `/mcp/servers` `/triggers` `/memories` 從「進階 ▼」下拉 → icon-only nav + hover tooltip（拿掉 60 行 dropdown 程式碼）
- **WorkspaceSwitcher / ProjectPicker / Modal** 全套 SIcon 化
- **ChatView 助理訊息**（#140）— hover 出「📤 展開」按鈕（≥600 字或含 ``` 才顯示）
- **Page transition**（#159）— 安全版（watch + CSS key toggle，無 Transition mode='out-in'，不會 race）+ scroll-top

### Fixed — Dark mode

- 🌓 **Dark mode token 100% coverage**（#142 + #147 + **#149**）— `bg-white` / `text-gray-*` / `text-slate-*` 全 0 殘留；**反轉 neutral 階層**一次修 352 處 hardcode
- WorkflowEditor 寫死 `#f0f2f5` 背景修為 `bg-surface-sunken`

### Fixed — Backend routing & schema

- **Gateway 沒 mount usage/triggers/mcp/memories**（#153）— 補 4 個 generic proxy
- **Agent LegacyURLBridge 缺 prefix**（#153）— 補 usage/triggers/mcp/memories/model-providers/media-providers/app-templates
- **Usage router mount prefix 缺 `/usage`**（#153）
- **MCP create SQL syntax**（#155）— asyncpg dialect 對 `:param::jsonb` 處理 bug，改 `CAST(:param AS jsonb)`
- **long_term_memories legacy schema**（#155）— 加 6 個 ALTER TABLE ADD COLUMN IF NOT EXISTS + user_id UUID 型別轉換

### Performance

- **ChatLayout 1022→9 KB** (-99%)（#146）— ArtifactPane defineAsyncComponent + `v-if="artifact.isOpen"`
- **md-vendor 1009→200 KB** (-80%)（#146）— `highlight.js/lib/common` 替代預設 192 languages
- **WorkflowEditor 66→33 KB** (-50%)（#162）— NodeConfigPanel defineAsyncComponent
- 拆 vendor chunks：`md-vendor`、`lf-vendor`、`vue-vendor`

### Docs

- `docs/qa/dark-mode-checklist.md`（#147）
- `docs/qa/visual-sweep-sprint19-20.md`（#163）
- `docs/plans/observability-plan.md`（#163）— metrics dashboard + E2E test 落地藍圖
- `docs/plans/next-direction.md`（#163）— 14 個下一步選項 + 4 推薦組合 + 4 anti-rec
- ui-kit README + Storybook 修 build（早期 + #138）

### Removed

- 「進階 ▼」 dropdown component（#150）— 改為 4 個 icon-only nav
- 多餘 `advancedOpen` state / `onClickOutside` / `isAdvancedActive` computed

### Security

- CAPTCHA 防暴力登入（#161）
- 401 interceptor 防遞迴 / 並發去重（#156）
- `?next=` redirect 限制必須 `/` 開頭（防 open redirect）

### Lessons learned（教訓）

- **「empty state ≠ 真.通」** — PR #148 / #151 前端 UI 落地後仍 404，因為 routing 沒接。教訓：endpoint UI 落地前 至少 curl 一次 POST/PUT。
- **Design system alias > raw scale** — 352 處 `bg-neutral-200` hardcode 不會 flip；改 11 行 token 反轉 neutral 階層比改 352 行 .vue 安全。
- **「做完忘了曝光」很容易發生** — 7 個 mcp endpoint + 3 個 trigger 隔離功能完全沒入口。Audit router 表 → orphan 5 模組曝光 5 PR。

### Migration（v2.0 → v2.1）

無 breaking change。所有 DDL 是 idempotent ALTER。可直接 `safe-redeploy.sh --all`。

唯一注意：若 `long_term_memories` 表是 v2.0 之前建的（schema 不齊），bootstrap_ddl 會自動補欄位 + UPDATE 補預設 workspace_id。

### PR refs（按 merge 時序）

#139 #140 #141 #142 #143 #144 #145 #146 #147 #148 #149 #150 #151 #152 #153 #154 #155 #156 #157 #158 #159 #160 #161 #162 #163

---

## [2.0.0] — 2026-05-17（GA）

> staffKM v2 — Enterprise AI Knowledge Management Platform
> 105+ PR、14 RFC、5 milestones（M1~M5）全部達標的 GA。

### Highlights

- **企業級多租戶**：workspace + 4 階 RBAC + 三層資料隔離（Path/RBAC/SQL）
- **30+ Workflow Nodes**：含 5 種 Workflow Manager（simple / retry / parallel / batch / sandbox）
- **25+ Model Providers**：地端 Ollama 預設；專屬 adapter for Anthropic / Gemini / Cohere / Bedrock / Vertex AI / MiniMax；其餘走 OpenAI-compatible
- **5+ Media Providers**：DALL-E / Stability / Whisper / OpenAI TTS / ElevenLabs
- **Token 計帳 + Quota**：tiktoken 精算、月度 cap、429 hard-limit、Admin dashboard
- **Sandbox 隔離**：subprocess + rlimit + timeout（RFC-010）；M4-A 升 nsjail
- **完整 Observability**：OTel collector + Prometheus + Grafana + Jaeger（RFC-012）
- **長期記憶 / 排程觸發 / MCP Hub**：M4 啟動
- **完整文件**：personas / brand guide / 12 篇 user/admin/dev guide / Backup-DR runbook
- **Python SDK + admin CLI**：`pip install staffkm-sdk staffkm-cli`
- **Helm chart**：HPA + SSE-friendly ingress + secret 管理

### Added — 完整功能清單

**M1（多租戶 + Folder + 設計系統）**
- workspace + member + role 表 + middleware（PR #51~54）
- 三層隔離（Path / RBAC / SQL ScopedQuery）
- Generic CRUD factory 雙端（make_crud_router / makeCrud<T,C,U>）
- 4 種模組：Tool / Skill / Data Source / Folder（PR #61~70）
- D-1 Tool 試跑、D-2 Skill 模板、D-3 DataSource 連線測試、D-4 share link、D-5 folder、D-6 markdown、D-7 application 版本控制
- i18n zh-TW / en 雙語字典（PR #98）
- Brand Guideline v1 + logo SVG + favicon（PR #99）
- UX 研究（personas / interview template / JTBD 對照）（PR #100）
- 設計系統 v1.1：⌘K Command Palette + dark mode token alias（PR #101）

**M2（Workflow Engine v2）**
- 30+ node types 與 dispatch（PR #75）
- 5 種 Workflow Manager（PR #76 + #82：parallel/batch 真實 asyncio.gather）
- LogicFlow 編輯器升級：undo/redo + snap + clipboard + 快捷鍵（PR #91）
- Sandbox 隔離（subprocess + rlimit）+ shell 節點 + RFC-010（PR #92）
- Workflow 版本控制

**M3（Model Hub）**
- BaseProvider 抽象 + 25 family registry + RFC-009（PR #79）
- 7 家專屬 adapter：Anthropic / Gemini / Cohere / Bedrock / Vertex AI / MiniMax + OpenAI-compat（PR #86 #87 #89）
- application_agent 接 get_adapter()（PR #86）
- Admin UI 串 registry 下拉（PR #83）
- Token 計帳 + Workspace Quota（PR #84）
- chat_stream 接 record_usage + 429 quota check（PR #88）
- 用量儀表板 UI（/admin/usage）（PR #90）

**M4（進階能力 — 啟動）**
- Media Provider 抽象（DALL-E/Stability/Whisper/TTS/ElevenLabs）（PR #93）
- Long-term Memory Store（DDL + CRUD + 全文搜尋）（PR #94）
- Event Triggers + 60s background worker（PR #95）
- MCP Hub（servers + tools cache + JSON-RPC client）（PR #96）
- 整合層 RFC-011（PR #97）

**M5（GA Release）**
- OTel collector + 6 條 alert + Grafana dashboard + RFC-012（PR #106）
- Helm chart 雛形 + Backup/DR runbook（PR #107）
- Python SDK + admin CLI + OpenAPI dump 腳本（PR #108）
- VitePress docs site + 12 篇 guide（PR #109）
- Demo seeder + Marketing landing（PR #110）

**工程基礎**
- CI（pytest + ruff + mypy + vue-tsc + Playwright + Trivy + Gitleaks）— PR #102
- pgvector 壓測腳本 + 報告模板（PR #103）
- API key Fernet 加密層（PR #104）
- tiktoken 精確計費（PR #105）

### Changed
- 從 v1 對話介面整體重構為對話為中心（claude.ai 對標）
- LegacyURLBridge：v1 → workspace-scoped 自動重寫，Deprecation header
- 全域 alert/confirm 部分替換為 useToast / useDialog（A11y dialog）

### Security
- API key 預設走 Fernet 對稱加密（環境變數 `STAFFKM_SECRETS_KEY`）
- Workflow `shell` 節點僅在 `workflow_manager='sandbox'` 下執行
- argv 必須絕對路徑；rlimit + timeout 強制
- Quota 超額 hard-cap 429（不只 warning）
- 多租戶三層隔離，每個 query 經 `WorkspaceScopedQuery`

### Known limitations
- **trigger_worker 多副本**：目前單副本（advisory lock 留 v2.1）
- **MCP server SSRF**：尚無 outbound allow-list（留 v2.1）
- **dark mode 全量化**：tokens 就位，部分 view 仍寫死 `text-gray-*`（清單在 `docs/design/dark-mode-checklist.md`）
- **eslint / vitest**：CI 為 stub（type-check vue-tsc 已強制）
- **embedding memory recall**：M4 啟動只有全文檢索，向量檢索留 M4 中段

### Migration（v1.x → v2.0）
1. `helm upgrade` 會自動跑 `bootstrap_ddl`（idempotent）
2. v1 URL 仍可訪問（LegacyURLBridge 重寫 + Deprecation header）；建議 90 天內客戶端切到 v2 URL
3. 既有 application 的 model 設定自動沿用；無 provider_type 走 OpenAI-compat fallback
4. API key 既有 base64 / 明文資料相容；逐步走 `encrypt_secret` 替換

## v1.x（legacy）

見 `docs/legacy/CHANGELOG-v1.md`（保留歷史；v2 GA 後不再 backport）。
