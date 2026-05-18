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

## 跑過的踩雷集（不要再踩）

| 雷 | 結論 |
|---|---|
| 直接 import LogicFlow → ChatLayout chunk 飆到 1MB | 大型 dep 一定 manualChunks + 配 lazy 引入點 |
| 改 352 處 `bg-neutral-200` vs 改 11 行 token | 改 token 永遠優先 |
| 「empty state ≠ 真通」| 任何新 endpoint 上線前 curl POST 一次 |
| asyncpg `:param::jsonb` | 一律 `CAST(:param AS jsonb)` |
| Storybook 8 + vite 6 不自動掛 @vitejs/plugin-vue | 顯式在 main.ts viteFinal 注入 |
| 「進階下拉」UX 突兀 | 改 icon-only nav + hover tooltip |
| Token expiry 多 request 並發 → N 次 /refresh | 用 module-scoped promise 去重 |
| router-view + Transition mode='out-in' 連點 race | 改用 watch + CSS key toggle |

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
