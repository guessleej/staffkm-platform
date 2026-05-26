# staffKM — Claude project memory

> 這個檔案是給 Claude（或其他 AI 助理）在這個 repo 工作時讀的。
> 凝結 Sprint 14-25 的設計決策、踩過的雷、可重複套用的 pattern。

## 一句話定位

**staffKM** — 企業 AI 知識管理平台，對標 MaxKB 功能完整度、走 claude.ai 視覺風。
Monorepo（apps/* + services/* + packages/*），Vue 3 + FastAPI + PostgreSQL + Ollama 預設。

## 重要原則（決策快查）

### 1. dev 跟 production 用同一個 compose
- `infra/docker-compose.yml` 是主 file
- `infra/docker-compose.override.yml` 是 dev 自動套（compose 預設行為）
- `infra/docker-compose.production.yml` 是 prod overlay（手動 `-f` 加）
- `safe-redeploy.sh` 有 `--prod` flag 切換

### 2. 不擅自跑長時間下載
- Ollama models 重抓很慢、會佔頻寬
- 任何 `ollama pull` 都先問使用者確認

### 3. Token / 認證
- JWT in localStorage（access_token / refresh_token）
- 401 → 並發去重 refresh → 失敗 redirect `/login?next=...`
- CAPTCHA 連 3 次失敗才出（in-process counter，10min 窗口）
- OIDC SSO 借用 `user.ldap_dn` 欄存 `oidc:{sub}`，避免新加 DB column

### 4. Design system v2 — alias 優先
- **bg-surface-raised / text-fg / border-bd / text-fg-secondary** 是 token alias，會跟 dark mode flip
- **bg-neutral-200 / text-neutral-700** 也會 flip（v2.1 在 `.dark` 反轉整個 neutral 階層）
- 新 view 一律用 alias 或 neutral；不要寫 `bg-white` / `text-gray-*` / `text-slate-*`
- accent 色（bg-brand-50 / bg-warning-50 / bg-success-50）刻意全主題一致

### 5. Icon — 用 SIcon，不要 inline svg
- `import { SIcon } from '@staffkm/ui-kit'`
- 44 個 lucide-style icons + `currentColor` stroke
- 新 icon 加到 `packages/ts/ui-kit/src/components/SIcon.vue` 的 ICONS 字典
- 例外：LoginView 中心「知識圖譜」是設計性插圖，保留

### 6. Nav 一致性
- 主功能（對話 / 應用 / 知識庫 / 代理人）= text-with-icon HNavItem
- 進階工具（技能 / 工具 / 資料來源 / MCP / 排程 / 記憶）= **icon-only NavIconLink + hover tooltip**
- admin = text-with-icon HNavItem（限 admin role）
- 沒有「進階下拉」— 已 PR #150 拿掉

### 7. routing 三層必通
任何新後端 endpoint 上線前 checklist：
1. **agent / knowledge service** main.py 有 `include_router(...prefix=f"{_PREFIX}/...")`
2. **agent legacy_bridge.py** `_LEGACY_PREFIXES` 加 `/api/v1/{your-prefix}`（沒加 → URL 不會 rewrite 成 workspace 版）
3. **gateway main.py + _generic_proxy.py** 加對應 proxy（沒加 → 404）

**verify**：curl `POST /api/v1/your/endpoint` with auth header；確保拿 200，不要只看 frontend empty state。

### 8. SQL 寫 JSONB 用 CAST
- ❌ `:args::jsonb` — asyncpg dialect bug（cast 後 `$N` 跟 `:name` 混用）
- ✅ `CAST(:args AS jsonb)` — 語意一致、不會被 dialect translator 卡

### 9. Idempotent DDL — bootstrap_ddl.py 永遠 ALTER ... IF NOT EXISTS
- 舊 deploy schema 跟新 code 不一致時，CREATE TABLE IF NOT EXISTS **不會補欄位**
- 永遠用 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` 補
- 型別變更用 `ALTER COLUMN ... TYPE ... USING ...`
- 教訓：v2.1 long_term_memories table 缺 6 欄炸 → PR #155 補

### 10. Frontend performance
- 大 chunk lazy import (`defineAsyncComponent`)：ArtifactPane、NodeConfigPanel 都這樣處理
- Vendor chunks: lf-vendor（LogicFlow）/ md-vendor（marked + highlight.js）/ vue-vendor 各自獨立
- `highlight.js/lib/common` 取代預設 192 languages，省 800 KB
- 首進 /chat 載入 ~250 KB（gz 90KB）

### 11. 模型設定：admin/models 選了要「真生效」— `system_settings.default.*` → runtime 解析（v5.11.x）
`/admin/models` 的「設定預設模型」下拉只是把 model_name 存進 `system_settings.default.{llm,vision,rerank,embedding,stt}`。
**存進去 ≠ 生效** — 過去這些是 advisory（runtime 只讀 env）。要生效**必須**有對應的 runtime resolver：

- **default.llm** → `services/agent/app/core/base_agent.resolve_system_llm()`（base_agent + application_agent 都用）
- **default.vision** → `services/knowledge/app/core/runtime_models.resolve_vision_ocr()`（process_document ingest 時）
- **default.rerank** → `services/knowledge/app/core/runtime_models.resolve_reranker()`（search 未帶 reranker 時 fallback）
- **default.embedding** → `runtime_models.resolve_embedding()`（**讀 `embedding.active` 非 `default.embedding`**）。
  embedding 是**雙設定**：`default.embedding`=desired（UI 存）、`embedding.active`=已套用（重嵌 job 成功才寫）。
  **query 模型必須與索引模型一致** → runtime 一律讀 active；換模型走「全庫重嵌」流程，不是改設定即生效：
  UI 選 → `POST /knowledge/embedding/reindex {model_name}` → `core/reindex.py` 全庫重嵌（維度不符會 DROP index
  → ALTER 兩個共用 vector 欄 `paragraph_embeddings`+`kb_entities` TYPE vector(N) USING NULL → 重嵌 → 重建
  ivfflat；期間搜尋退化）→ 成功寫 `embedding.active` → runtime 起用。8 個 get_embedder 呼叫點全走
  `get_active_embedder(session)`。`GRAPH_EXTRACT`/embedder 容器各自獨立。
- **default.stt / default.tts** — 系統無對應 runtime pipeline；UI 標 `planned`（存了不生效）。
  （UI `/admin/models` 每個預設模型標 status badge：live / reindex / planned，避免「選了沒反應」誤會。）

Resolver 共同套路（新增 default.X 一律照做）：讀 `system_settings.default.X`（jsonb 字串或 `{model_name}`）→ JOIN `ai_models`(model_type=X)+`model_providers` 取 base_url/api_key → **env 後備**、查無設定回 None/env、DB 不可達不致命。每次請求重解 → 改設定按儲存即時生效、不需重啟。

雷點：
- **base_url 的 /v1**：ollama provider base_url 存「不帶 /v1」（verify 走原生 `/api/tags`）。OpenAI 相容聊天/vision 要 `/v1` → resolver 補上；reranker 走 `/rerank`、`/api/rerank` → **不補 /v1**。
- **`get_session()` 不能直接 `async with`**：它是 FastAPI 依賴用的 async generator。非 endpoint（resolver / Celery / base_agent）要用底層 `from staffkm_core.utils import database as _db; async with _db._session_factory() as s:`。
- **api_key 解碼**：auth 的 `models.py` 用 base64 存（`_encode_api_key`）；resolver 解 `base64.b64decode`。注意 `application_agent` 走的是 `decrypt_secret`（fernet:/plain:/legacy）— 兩套不一致是既有債，地端 ollama 免 key 不受影響。

### 12. Ollama 模型清單：不寫死，動態同步 `/api/tags`（v5.11.x）
- ❌ 不要在 `model_pricing.PROVIDER_DEFAULT_MODELS` / `auth models._DEFAULT_MODELS_ON_CREATE` / `registry.recommended_models` 寫死 ollama 模型名 — host 上沒有就變「抓不到的幽靈模型」，且 agent 啟動 seed 會一直種回來。
- ✅ `auth/api/models.list_provider_models` 對 ollama 型 provider 即時打 `/api/tags`，**多補少刪** self-heal（`_sync_ollama_models`）。model_type 靠關鍵字猜（embed→embedding / rerank→reranker / ocr·vision→vision / 其餘 llm）。
- Docker Desktop（Mac/Win）連 host ollama 用 `host.docker.internal:11434`（compose 內沒有叫 `ollama` 的服務；地端 embedding 容器叫 `embedder`）。
- ⚠️ Kimi（Moonshot）內容過濾會擋台灣/兩岸/政府公文（400 high risk）→ 台灣公文場景的系統 LLM / GraphRAG 抽取都改本機 ollama（gemma4:e4b / TAIDE 12B）。

### 13. 測試分層：輕量（每 PR）vs 整合（真 DB）+ 誠實 coverage gate（v5.12.x）
CI 測試**刻意分兩層**，別把它們混在一個 job（依賴衝突 + 慢）：

- **輕量層（`backend` job，每 PR 一定跑）**：最小依賴 `pytest/ruff/structlog/charset-normalizer`，**不裝** fastapi/sqlalchemy/asyncpg。
  跑：雷區守衛（`tests/test_landmine_guards.py` 純檔案掃描）+ 純邏輯單元（`test_workflow_conditions` / `test_secrets` / `test_search_fusion` / `test_document_processor`）。
  ⇒ 新單元測試要嘛**零重依賴**、要嘛 import 的模組依賴極輕（抽純函式出來測，如 `workflow/conditions.py`）。
- **整合層（`integration` job，backend 改才跑）**：`pgvector/pgvector:pg16` service container + 裝 `tests/integration/requirements.txt`（sqlalchemy/asyncpg/passlib/pyjwt/pydantic… 版本對齊各 service）。
  用 repo 真正的 `init_db()` + `_session_factory()` 對**真 PG** 做 SQL round-trip（連 asyncpg dialect 一起測）。已覆蓋：
  - `tests/integration/agent/` → quota/計帳（`app.core.usage`：record_usage / check_quota 雙層 / calc_cost / calc_media_cost），**100%**。
  - `tests/integration/auth/` → 登入大門（`app.core.auth_service`：本地密碼驗證 + 帳號狀態 + JWT access/refresh claims），**89%**（LDAP/AD 需 live AD、標 `# pragma: no cover`）。

整合測試規約（`tests/integration/{service}/conftest.py` + 共用 `_harness.py`）：
- **一個 service 一個 subdir、CI 各自一次 pytest invocation**：agent/auth/knowledge 都有 `app/` package，同 process 把多個 service 放上 sys.path 會 `import app.core.X` 撞名（同 backend job 拆 knowledge/agent 跑兩次的理由）。
- **沒設 `STAFFKM_TEST_DB_URL` 或沒裝重依賴 → 該 subdir collection 階段自動 skip**（`collect_ignore_glob`），且 conftest **不在 guard 外 import 任何重依賴**（含 `_harness`）→ 輕量 job 跑 `pytest tests/` 不會炸。
- schema 兩種來源、**都忠實零漂移**：raw-SQL 模組用「對齊 `\d` dump 的最小 DDL」；ORM 模組（如 auth）直接 `User.__table__.create()` 從 metadata 現建。**都不跑整條 alembic**（跨服務、22+ migration、慢且脆）。
- 每 test 一個 fixture（engine 在該 test 自己的 event loop 內 `init_db` → 避免 pytest-asyncio 跨 loop 共用 asyncpg 連線的 `InterfaceError`）；測前 TRUNCATE 清殘留。
- async 測試靠 `pytestmark = pytest.mark.asyncio`（strict 模式，不需 `-o asyncio_mode=auto`）。
- ⚠ **bcrypt 必須 4.0.1**：passlib 1.7.4 與 bcrypt 4.1+ 不相容（backend 偵測炸）；整合測試依賴版本要對齊 service requirements，否則測到的不是 production 行為。

**Coverage gate 哲學：誠實、不灌水**。`--cov` 範圍 = 該 subdir 真有測的模組（不報全 repo 假數字）。**門檻按各模組「CI 可測天花板」分別設**（quota 90 / auth 85）——不可測的外部整合（LDAP/AD…）標 `# pragma: no cover`，不用拉低門檻或假裝有測。新模組 → 加 subdir + 把模組加進 `--cov`。

整合測試實戰挖出的真 bug：**NULL `password_hash`（純 SSO/OIDC 帳號）走本地登入 → `pwd_ctx.verify(pw, "")` 丟 `UnknownHashError`（未捕捉 500）**。修為「`password_hash` 空 → 直接 deny」（fail-safe）。← 純邏輯單元測不出來、要真 round-trip 才現形。

本機重跑（CI 之外，每 subdir 各跑一次）：
```bash
docker run -d --name pg-itest -e POSTGRES_USER=staffkm -e POSTGRES_PASSWORD=staffkm_secret \
  -e POSTGRES_DB=staffkm_test -p 55432:5432 pgvector/pgvector:pg16
pip install -r tests/integration/requirements.txt
export STAFFKM_TEST_DB_URL=postgresql+asyncpg://staffkm:staffkm_secret@localhost:55432/staffkm_test
pytest tests/integration/agent --cov=app.core.usage        --cov-fail-under=90 -q
pytest tests/integration/auth  --cov=app.core.auth_service --cov-fail-under=85 -q
```

## 常用指令

```bash
# Dev
./tools/scripts/safe-redeploy.sh ui agent      # rebuild 指定服務
./tools/scripts/safe-redeploy.sh --all          # rebuild 全部
./tools/scripts/safe-redeploy.sh ui --no-build  # 不 build 只 recreate

# Production
./tools/scripts/safe-redeploy.sh --prod --all

# Build
cd apps/web && pnpm build                       # 約 4 秒
cd packages/ts/ui-kit && pnpm build-storybook   # ~2.5 秒

# 後端 DB
docker exec staffkm-postgres psql -U staffkm -d staffkm -c "\dt"

# 備份
./tools/backup/backup-postgres.sh
./tools/backup/backup-minio.sh
```

## Repo 結構

```
apps/
  web/           # Vue 3 SPA — vite + vue-router + pinia + tailwind
  docs/          # docs.staffkm site（待）
  marketing/     # 行銷站 Vue SPA — v4.2（landing/pricing/cases/about）
  admin-cli/     # `staffkm-cli` — v4.4 進階到 8 個 command group
services/
  gateway/       # API gateway + JWT auth middleware + reverse proxy
  auth/          # /auth/{login,refresh,me,oidc/*}
  agent/         # Applications / Workflows / Projects / Triggers / MCP / 模板 / Quota / Memory / ...
  knowledge/     # KBs / Documents / Paragraphs / Search / Hit-test / Web sync / Inline write
  chat/          # Conversations / Messages
  integration/   # LINE / Teams webhooks
  embedder/      # Ollama 容器（bge-m3 預設）
packages/
  ts/
    design-tokens/   # HSL CSS vars + Tailwind preset
    ui-kit/          # 34 Vue 3 components + 44 SIcon names + Storybook
  ts/
    staffkm-sdk/     # `@staffkm/sdk` — v4.5 TypeScript SDK
  python/
    staffkm-core/    # 共用 schemas / response / database / observability / audit / arq
    staffkm-tenant/  # TenantContext middleware + workspace RBAC
    staffkm-sdk/     # `pip install staffkm` — v4.5 完整 SDK + 既有 staffkm_sdk legacy
    staffkm-plugin-sdk/  # v4.3 plugin authoring SDK (BaseNode/Provider/Hook)
infra/
  docker-compose.yml              # 主 compose
  docker-compose.override.yml     # dev override（auto-applied）
  docker-compose.production.yml   # prod overlay（手動 -f）
  caddy/Caddyfile                 # prod TLS reverse proxy
  nginx/                          # dev nginx
  monitoring/                     # prometheus.yml + grafana provisioning
  helm/                           # K8s chart（v2.0 已落地）
tools/
  scripts/safe-redeploy.sh        # 解 502 共業 + autoheal
  backup/                         # PG + MinIO backup/restore
  starter-pack/                   # v4.1: 5 個預建 application JSON
  sales-demo/                     # v4.1: seed_demo.py + 10min demo-script.md
  plugin-marketplace/             # v4.3: index.json registry
  eval/                           # v3.3-C5: RAG eval harness + dataset
  terraform-provider-staffkm/     # v4.4: TF provider scaffold (Go)
  sdk-go/                         # v4.5: Go SDK
  seed-marketplace.py             # v4.10: marketplace seed placeholder
docs/
  user-guide/                     # 給最終使用者
  deploy/                         # 給部署 / DR / multi-region / active-active
  plans/                          # 計畫文件（v2.x ~ v5.0 roadmap 全在）
  qa/                             # checklist
  rfc/                            # 14 篇歷史 RFC
  dev/                            # 開發者：observability / alembic / plugins / cli / sdks / reranker / idempotency / ai-workflow-gen / workflow-marketplace
  perf/                           # v3.3-C5: RAG bench history
  upgrade/                        # v3→v4 / v4→v5 upgrade guides
```

## v3.x+ 新元件速查

| 領域 | 元件 | 引入版本 |
|---|---|---|
| Auth | Redis CAPTCHA / OIDC schema | v3.0 |
| Schema | alembic 0001-0019（共 19 個 revision） | v3.1+ |
| Cost | `meter_llm_call` / `meter_media_call` + `model_usage_logs.feature` | v3.2 / v3.4 / v3.7 |
| Quota | `workspace_quotas` / `user_quotas` / `quota_alerts` + alert worker | v3.2 / v3.3-D |
| Observability | OTel auto-instrument + Loki + slow query trace | v3.3-B / v3.7-P4 |
| Workflow | run_step persistence / human_approval / sub_workflow / arq workers | v3.5 / v4.0-P3 |
| Resilience | webhook_outbox / Idempotency-Key middleware / graceful shutdown | v3.6 |
| Billing | Stripe 4 表 / nightly usage report | v4.7 / v4.8 |
| Self-service | trial signup / email verify / OAuth (Google+GitHub) | v4.1 / v4.6 |
| Multi-region | PG read replica + active-active scaffolding | v4.0 / v5.0 |
| Ecosystem | Plugin SDK / TF provider / Python+TS+Go SDK | v4.3 / v4.4 / v4.5 |
| AI features | LLM-as-judge eval / AI workflow gen / Workflow marketplace | v3.7-P3 / v4.9 / v4.10 |
| Test depth | 整合測試層（真 PG）+ 誠實 coverage gate：quota / auth | v5.12.6 / v5.12.7 |

## 跑過的踩雷集（不要再踩）

| 雷 | 結論 |
|---|---|
| 直接 import LogicFlow → ChatLayout chunk 飆到 1MB | 大型 dep 一定 manualChunks + 配 lazy 引入點 |
| 改 352 處 `bg-neutral-200` vs 改 11 行 token | 改 token 永遠優先 |
| 「empty state ≠ 真通」| 任何新 endpoint 上線前 curl POST 一次 |
| asyncpg `:param::jsonb` / `:emb::vector` 等 dialect 不認，exception 被 starlette 吞、500 沒 log | 一律 `CAST(:param AS jsonb)`、`CAST(:emb AS vector)`；v5.0.10 全 repo 掃修 19 處 |
| asyncpg array bind 用 PG literal `'{u1,u2}'` 也壞 | 用 Python list 直接 bind：`{"ids": [uuid1, uuid2]}` 配 `ANY(:ids)` |
| Storybook 8 + vite 6 不自動掛 @vitejs/plugin-vue | 顯式在 main.ts viteFinal 注入 |
| 「進階下拉」UX 突兀 | 改 icon-only nav + hover tooltip |
| Token expiry 多 request 並發 → N 次 /refresh | 用 module-scoped promise 去重 |
| router-view + Transition mode='out-in' 連點 race | 改用 watch + CSS key toggle |
| 跑了 v3-v5 十幾個 milestone 才發現 `/admin/users` 跟 `/admin/system` 一直是 `UnderConstructionView` placeholder（v5.0.1 才補）| 廣度做了、深度沒收尾的典型債 — 加進下面 release checklist |
| NOT NULL JSONB / 陣列 column INSERT 帶 None → `NotNullViolationError` 被 starlette 吞、前端只看到 generic「儲存失敗」 | INSERT 時 fallback 用 `'{}'` / `'[]'` 字串，**不能傳 None**；v5.0.13 從 admin/models 新增 Moonshot provider 修出 |
| Gateway router 透明 forward `/api/v1/foo/{path}` → agent / knowledge service v4.0 後只接 workspace-scoped `/api/v1/workspace/{ws}/foo/...` → 404 / 卡死 | 寫 gateway router 必須注入 `X-Workspace-ID` header → workspace prefix。pattern 看 `routers/agent.py` / `routers/knowledge.py` 的 `_target()`；v5.9.10 / v5.9.16 / v5.9.17 三輪修補（agent / chat / knowledge / applications / api_keys / projects 都中過） |
| 前端 raw `fetch()` 繞過 axios interceptor → 漏 `X-Workspace-ID` header → gateway 退回 legacy → 後端 404 → 對話 stream 空回應 | 任何前端 raw fetch 都要手動注入 ws header。`apps/web/src/api/chat.ts` 用 `dynamic import('../stores/workspace')` 拿 `currentId`；v5.9.14 從「對話無法回應」修出 |
| Chat service 沒有 GatewayHeadersMiddleware → 所有 conversation 的 `user_id` 都 fallback `"anonymous"` → 跨 user 不隔離 + ownership check 失敗 | 任何 backend service 接 user-scoped resource 都要 GatewayHeadersMiddleware（從 X-User-ID header 寫 request.state.user_id）；v5.9.13 從「刪掉的對話又出現」修出 |
| LLM 端 vendor 自動掃描公開通訊中的 sk-XXX 格式 key 並 auto-revoke | API key **永遠**只能進系統 settings 畫面，不能貼到任何對話 / Slack / GitHub / Notion；debug 時只貼前後 6 字元 |
| 新 Celery task 沒在 `celery_app.task_routes` 加 queue 路由 → 進 default queue、worker（`-Q knowledge`）收不到、任務**永遠不跑**（embedding reindex 中過；`tests/test_landmine_guards.test_celery_tasks_have_queue_route` 固化）| 每個 `@celery_app.task(name="app.tasks.X.Y")` 都要有對應 `"app.tasks.X.*": {"queue": "knowledge"}` 路由 |
| embedding 換不同維度模型 → 兩個共用 vector 欄（`paragraph_embeddings`+`kb_entities`）都要遷移、否則圖錨定壞 | 走 `core/reindex`：DROP index → ALTER 兩欄 TYPE vector(N) USING NULL → 全庫重嵌（含 kb_entities）→ 重建 ivfflat。先用 ROLLBACK 交易 dry-check ALTER 語法 |
| admin/models 選了預設模型「按了沒反應」— runtime 只讀 env，settings 是 advisory | 新增 default.X UI 選擇器**同 PR** 要接 runtime resolver（見原則 §11），否則別讓 UI 看起來會生效 |
| 非 endpoint 程式 `async with get_session()` 炸 `'async_generator' object does not support ...` | `get_session` 是 FastAPI 依賴；resolver/Celery/base_agent 改用 `_db._session_factory()`（見 §11）|
| ollama provider verify 紅燈 `Name or service not known` / `HTTP 404` | base_url 要 `http://host.docker.internal:11434`（**不帶 /v1**，verify 走 `/api/tags`）；registry 預設別寫成 `http://ollama:11434/v1`（無此 host + /v1 多餘）|
| admin/models 一直冒出 host 上不存在的 ollama 模型（llama3.1/qwen2.5…）| 別在 seed/registry 寫死 ollama 模型；靠 `/api/tags` 動態同步（見 §12）。agent 重啟會把寫死的種子一直種回來 |
| GraphRAG「graph-only 段落擠掉正確 hybrid 命中」看似權重問題 → 真因是 `ivfflat.probes=1`（pgvector 預設）讓 hybrid 召回崩壞、graph 在替它擦屁股；且外部 A/B harness 的 copy bug 偽造了退步 | 向量查詢一律 `SET LOCAL ivfflat.probes`（settings 可調，≈sqrt(lists)）；融合的 `by_id` 必須持 all_results 同一 ref；graph 權重別調低（會砍增益）。v5.11.4 修，`tools/eval/graphrag_ab.py` + `test_search_fusion.py` 守 |

## Release checklist（每個 tag 前**必跑**）

每個 minor / patch release 前，下面兩條**不能跳**：

```bash
# 1. 沒有殘留的 placeholder view（或必須有對應 backlog ticket）
grep -rl "UnderConstructionView" apps/web/src/
# 預期：no matches（exit 1）

# 2. 點過每個 nav item，確認有真實內容
grep -cE 'to="/[a-z]' apps/web/src/views/dashboard/DashboardLayout.vue
# 拿到數字 N → 手動點過 N 個 nav，每個都要看到非 placeholder 內容

# 3. asyncpg dialect 雷掃描（CLAUDE.md §8 紀律）— 避免 500 沒 log 的悶炸
#    v5.10.5：pattern 補 f-string 內插變體 :{var}::type（原本只抓字面 :name::type，
#    害 _generic_crud / app_versions 的 :{col}::jsonb 潛伏；test_landmine_guards 同步強化）
grep -rnE ':\{?[a-z_][a-z0-9_]*\}?::(jsonb|vector|uuid|int|text|timestamptz|date|inet|bool)' \
    services/ packages/python/ --include="*.py" 2>/dev/null \
    | grep -v __pycache__ | grep -v "/alembic/versions/"
# 預期：no matches。有的話一律改 CAST(:param AS type)

# 4. asyncpg array literal 也要禁
grep -rnE "ANY\(['\"]\\\\?\{[a-z0-9_,\\-]+\}['\"]\)" services/ --include="*.py" 2>/dev/null
# 預期：no matches。改用 Python list bind: {"ids": [u1, u2]} + ANY(:ids)

# 5. 檢查 NOT NULL JSONB INSERT 沒有 None fallback（CLAUDE.md 踩雷集新加）
grep -rnE "json\.dumps\([^)]+\) if [^)]+ else None" services/ --include="*.py" 2>/dev/null
# 預期：no matches（應該是 else '{}' 或 else '[]'，避免 NotNullViolationError 被 starlette 吞）
```

額外建議：
- 每 5 個 minor 跑一次完整 frontend grep：`UnderConstructionView` / `TODO` / `placeholder` / `coming soon`
- nav 加新 entry **同 PR** 內要包含對應 view 真實實作（不准先 placeholder 後補）
- 跑 milestone 規劃時，先 `ls apps/web/src/views/` 對比 nav，找出「有 view 但 placeholder」或「無 view 但 nav 已建」的缺口

## 命名 / 語氣

- 使用者面向文案 → 繁體中文（zh-TW），跟系統設計一致
- 簡中（zh-CN）/ 英文（en）有但機械轉換，重要 demo 用 zh-TW
- commit message：Conventional commit (`feat:` / `fix:` / `perf:` / `chore:` / `docs:`)
- PR title：跟 commit title 一致；body 用 markdown 表格 / Test plan checklist
- 文件用 Markdown，emoji 善用（圖示識別性）

## 重要 PR / Tag 對照

### v2.x — GA + B2B
| Tag | 範圍 | 重點 |
|---|---|---|
| v2.0.0 | 105+ PRs | GA — 完整功能 + 30+ workflow nodes + 25+ provider + Helm |
| v2.1.0 | #139-#163 | MaxKB-parity 5 缺口全關 + Orphan endpoints 5 模組 + Design system v2 |
| v2.2.0 | #165-#168 | Production-ready: metrics + Caddy auto-TLS + backup SOP |
| v2.3.0 | #169-#170 | Demo polish: onboarding wizard + citation chip UI |
| v2.4.0 | #171-#172 | B2B: embed widget + OIDC SSO + 8 user docs |
| v2.5.0 | #173-#174 | 開發夥伴: CLAUDE.md + API ref + template marketplace |

### v3.x — Production hardening
| Tag | 範圍 | 重點 |
|---|---|---|
| v3.0.0 | #175-#179 | Auth/CAPTCHA Redis + OIDC schema + Audit log + Grafana + Playwright E2E |
| v3.1.0 | #180-#184 | Technical debt cleanup: alembic baseline + audit wiring + LegacyURLBridge default 410 |
| v3.2.0 | #185-#189 | Cost/Quota governance: ai_models pricing + meter_llm_call + admin Quota UI |
| v3.3.0 | #190-#198 | A+D+B+C mega: workflow metering / user quota / OTel+Loki / RAG reranker+eval |
| v3.4.0 | #199-#204 | v3.3 留尾: 4 non-LLM node metering + SMTP + cross-encoder reranker + CI bench |
| v3.5.0 | #205-#210 | Workflow expansion: run step persistence + human_approval + sub_workflow + history UI |
| v3.6.0 | #211-#216 | Async resilience: webhook outbox + task heartbeats + Idempotency-Key + graceful shutdown |
| v3.7.0 | #217-#222 | Cost attribution: per-conversation cost + feature label + LLM-as-judge + slow query trace |
| v3.8.0 | #223-#228 | v3.7 留尾: workflow conv_id + admin billing UI + multi-judge + query plan analyzer |

### v4.x — Major + Business + SaaS
| Tag | 範圍 | 重點 |
|---|---|---|
| v4.0.0 | #229-#235 | 拔 bootstrap_ddl + LegacyURLBridge + arq workers + active-passive multi-region |
| v4.1.0 | #236-#237 | A: trial signup + 5 starter packs + sales demo |
| v4.2.0 | #238 | B: marketing SPA (landing/pricing/cases) |
| v4.3.0 | #239 | C: Plugin SDK (BaseNode/Provider/Hook) + marketplace registry |
| v4.4.0 | #240 | D: staffkm-cli 8 groups + Terraform provider scaffold |
| v4.5.0 | #241 | E: API SDK Python/TS/Go (24 endpoints each, streaming chat) |
| v4.6.0 | #242 | F: email verify + forgot password + Google/GitHub OAuth |
| v4.7.0 | #243 | G: Stripe billing (subscription + topup + portal + webhook) |
| v4.8.0 | #243 | H: usage-based metered billing (nightly aggregation worker) |
| v4.9.0 | #244 | I: AI-generated workflow (自然語言 → workflow JSON + LogicFlow apply) |
| v4.10.0 | #245 | J: workflow marketplace (跨 org public gallery + ratings) |

### v5.x — Active-active multi-region
| Tag | 範圍 | 重點 |
|---|---|---|
| v5.0.0 | #246 | K: scaffolding (region middleware + CRDT helper + admin UI + conflict log) — disabled by default |
| v5.1+ | future | region steering / 真 CRDT / conflict UI / failover automation |

### v5.11.x — GraphRAG + 地端模型治理
| Tag | 範圍 | 重點 |
|---|---|---|
| v5.11.0 | #321 | GraphRAG 加法層 MVP（RFC-014）+ 混合語料分流（looks_like_form）+ ODF(.odt) 支援 |
| v5.11.1 | #322 | Ollama 接本機 + admin/models 動態同步 `/api/tags` + 系統預設聊天模型接 runtime + Big5/CP950 編碼偵測 |
| v5.11.2 | — | vision OCR 接 runtime（default.vision）+ Big5 CI 守衛 |
| v5.11.3 | — | reranker 接 runtime（default.rerank） |
| v5.11.4 | — | GraphRAG 召回調校：修 `ivfflat.probes`（根因）+ graph-only cosine 門檻 + 融合重構（可測） |
| v5.11.5-15 | — | 測試/CI 硬化：E2E（ingest→檢索）、SSE 換行根因修+多層守衛、RAG retrieval 回歸 gate、Decimal/advisory/asyncpg/ollama-/v1/get_session/celery-route landmine 守衛、Playwright 對話渲染、nightly cron（self-hosted gated）|
| v5.11.16 | — | **GraphRAG 進階 Phase 1**：持久化實體關係（kb_relations + relation_mentions co-occurrence grounded）|
| v5.11.17 | — | **Phase 2**：多跳召回（沿 kb_relations 擴 1 跳）+ hop0/hop1 A/B。**預設 `GRAPH_QUERY_HOPS=0`**（小語料增益=0、文件內共現鄰居共用段落；evidence-gated，語料變大再開）|
| v5.11.18 | — | **Phase 3**：community detection（連通分量分群 + 每社群 gemma4 摘要 → kb_communities）+ `GET /graph/communities` |
| v5.11.19 | — | **embedding 熱換**：runtime 解析（active/desired 雙設定）+ 全庫重嵌 pipeline + 維度遷移 + 進度 + celery-route 守衛 |
| v5.11.20-21 | — | 引用 hover 暗框移除（改原生 title tooltip、不蓋主區）|
| v5.11.x UI | — | A：HitTest 加「GraphRAG 為加法層」說明；B：admin/models 嵌入模型「套用（全庫重新索引）」按鈕 + 進度 |

**GraphRAG A/B 實測（台灣公文「完整語料」KB f3281a2b，5 query，gemma4 抽的實體）**：
- 召回門檻 `tools/eval/graphrag_ab.py`（忠實版，直接 import 真實 `_fuse_graph_results`）。
- **v5.11.4 修正後**：平均 recall@5 base(hybrid) **0.40 → graph 融合 0.88**，**0 退步**（5 題全進步或持平；原本看似退步的性平題 0.80→1.00）。
- graph 仍主要補「召回/路由」：把 hybrid 漏掉的相關段落補進 top-k（如教育部司題 0.00→0.80）。
- 數字精確性：graph 只回 paragraph_id，答案仍由 LLM 讀**原始段落內容**（`_score_paragraphs_by_ids` 回 `p.content` 原文）→ 不經 graph 改寫，數字不失真（符合 RFC-014 設計）。

**v5.11.4 調校三件事（重要：別再走回頭路）**：
1. **根因是 `ivfflat.probes=1`（pgvector 預設），不是融合權重**。只掃 1 個倒排清單 → hybrid 召回極差（base 0.12）且對 embedding 微擾敏感（同 query 不同 process 可能 0 筆 vs 全中）。設 `IVFFLAT_PROBES=10`（≈sqrt(lists)），每條向量查詢以 `SET LOCAL` 套用（pooling 安全）→ base 0.12→0.40。`hybrid_search` 與 `graph_anchored_paragraph_ids`（kb_entities 也走 ivfflat）都套。
2. **`_GRAPH_RRF_WEIGHT` 維持 1.0，不要調低**。A/B 實證：W_only≤0.5 時 graph-only 進不了 top-k → graph 增益**整個歸零**（0.88→0.40）。增益全靠 graph-only 擠掉「錯的」hybrid 命中。
3. **graph-only 設 cosine 門檻（= `similarity_threshold`，預設 0.5）**：低相關 graph-only 不得併入，防呆但增益全保（門檻>0.55 才開始侵蝕）。交集（hybrid∩graph）一律加分（共識）。
- ⚠ 「退步」曾被外部 harness 誤判：`merged_top` 用 `dict(r)` copy 建索引、boost 寫進孤兒物件 → 交集加分遺失、正確命中被擠掉。真實 `search.py` 的 `by_id` 必須持 all_results 的**同一 ref**（已收斂進 `_fuse_graph_results` + 單元測試 `test_search_fusion.py` 守住）。

## 跟使用者溝通

- 預設繁體中文台灣，除非他切換到 en / zh-CN
- 簡潔直接，不要 puff
- 用清單 / 表格 / 程式碼塊
- 重要的數字加粗（`**42 KB**`）
- 「跳過 / 故意保留」要明確標 — 不要假裝沒看到

## 不要做的事

- 不要主動 `git push` 沒 review 過的 commit
- 不要 commit `.env.production`（真實 secret）
- 不要動 LoginView 中心知識圖譜插圖（intentional design）
- 不要在 PR body 寫「使用者點頭就 merge」之類粗暴
- 不要 reformat 整檔（只改 relevant 段落）
- 不要無預警跑 `pnpm install` 加新 dep（先問或寫進 PR）
