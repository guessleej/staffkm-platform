# staffKM — Session 接手交接（貼到新對話用）

> 給新對話的 Claude：先讀 repo 根目錄 `CLAUDE.md`（專案記憶，含設計決策/踩雷集/tag 表），
> 再讀本檔補「最近這輪做了什麼 + 一個還沒結案的問題」。本檔位置：`docs/dev/SESSION-HANDOFF.md`。

## 0. 專案一句話
staffKM — 企業 AI 知識管理平台，Monorepo（apps/web Vue3 + services/* FastAPI + PostgreSQL/pgvector + 本機 Ollama 預設）。
Repo：`github.com/guessleej/staffkm-platform`，工作分支 `main`。

## 1. 這輪（v5.12.6 → v5.12.26）做了什麼 —「測試深化 + 生產硬化」

**整合測試層（真 PG/pgvector，`tests/integration/{service}/`，每服務各自 pytest invocation）**，已覆蓋 DB-backed 模組：
- agent：quota/計帳(`app.core.usage` 100%)、workflow executor 編排核心、webhook_outbox 投遞狀態機、idempotency 去重中介層、quota 並發 TOCTOU、human_approval/resume 狀態機、trigger_dispatcher claim 去重
- auth：登入/JWT(`app.core.auth_service`)
- knowledge：hybrid 檢索(`app.core.vectorstore` 100%)
- chat：對話 ownership 跨 user 隔離（list/delete/get_messages/stream/share IDOR）
- 純邏輯單元（輕量 CI、無 DB）：crdt（active-active 衝突解決）、workflow_conditions、secrets、search_fusion
- CI：`integration` job（pgvector container）每模組誠實 per-gate；輕量 `backend` job 跑 landmine(13 條)+純單元。conftest 規約見 CLAUDE.md §13。

**整合測試實戰挖出並修的 5 個真 bug（重點）**：
1. auth：NULL `password_hash`（純 SSO 帳號）走本地登入 → `pwd_ctx.verify("")` 未捕捉 500 → 改空 hash 直接 deny
2. reindex：embedding 熱換 active-ordering → 維度錯配（已於更早修）
3. webhook_outbox：naive `datetime.utcnow()` 寫 timestamptz → 非 UTC session 排到過去 → 狂發；改 server-side `now()+make_interval`
4. **chat `get_messages` read-IDOR**（知道 conv_id 就能讀別人對話）→ 補 ownership check
5. **chat `stream_message` write-IDOR**（往別人對話塞訊息）→ 補 ownership check

**真跑過（非紙上談兵）**：
- `tools/perf/scale_validation.py`：100k 段落/10KB/1024d pgvector，p50/p95/p99/並發/KB 隔離（報告 `docs/perf/v5.12-scale-validation.md`）。發現：probes=10 在 10 萬量級 ~6× 延遲；ivfflat 建索引吃 `maintenance_work_mem`。
- `tools/backup/dr-drill.sh`：backup→restore→md5 驗證 PASS。
- `tools/backup/replication-failover-drill.sh`：串流複製→promote failover PASS（資料層 active-passive）。

**工具就緒、需 served stack 才真跑（誠實標、未混充跑過）**：
- `tools/perf/load_test.js`（k6 全棧壓測）+ runbook `docs/perf/load-test.md`。

**清掉的既有債**：
- API key 加解密收斂單一來源 `staffkm_core.secrets`（encrypt/decrypt_secret，全 reader/writer 統一，舊 base64 向後相容；landmine 守 raw base64）
- `default.stt/tts` planned→live（`base_agent.resolve_media_default` + workflow 節點 fallback）
- dev HTTPS：nginx :443 自簽（`infra/nginx/ssl/gen-dev-cert.sh`）；prod Caddy 本就有 TLS+HSTS

**前端 UI 連環修（v5.12.24–.26，皆已部署 ui）**：
- **v5.12.24** chat deep-link：`/chat?conv=<id>` 直接開/重整空白。根因：`ChatView.selectFromRoute` 只在記憶體清單找、無 by-id 退路 + 後端無單一對話詳情端點。修：後端加 `GET /chat/conversations/{id}`（回 application_id/scenario_id/kb_ids + ownership）+ 前端 `fetchConversationById` + `selectFromRoute` fallback。+3 整合測試。
- **v5.12.25** 串流中切頁返回回答消失：返回時 `selectConversation()` 清空 messages + `fetchMessages` 覆蓋 → 抹掉進行中的回答。修：`selectFromRoute` 開頭守衛——返回「正在串流的同一對話」時不 wipe/refetch（背景 streamChat 續跑、保留訊息）。
- **v5.12.26** 工具/管理 popover 同時開（兩條選單）：`NavMenuPopover` 按鈕 `@click.stop` → 不冒泡到 document → 兄弟 popover 的 `onClickOutside` 收不到 → 不互斥。修：拿掉按鈕 `.stop`（面板的 `.stop` 保留）。

## 2. Git / 部署狀態
- `main` 已 push 到 `v5.12.26`（與 origin 同步）。
- **已重新部署**：`ui`（最新含 .24/.25/.26 前端修）+ `chat`（.24 deep-link/IDOR）。
- **未重新部署**：`agent`（仍是舊 code，Up 42h）— 所以 API key 單一來源(v5.12.11)等 agent 改動**還沒 live**，但不影響運行（舊 decrypt_secret 仍在舊容器內、行為相容）。
- 重新部署指令：`./tools/scripts/safe-redeploy.sh <service...>`（如 `ui chat`）。

## 3. 一連串「前端 client-side 故障」的共同結論（重要）
今天使用者連續回報：deep-link 空白 / 串流消失 / 雙選單 / chat「回不出來」/ 文件清單空。
**後端每次都實測健康**（chat→agent→gemma4 0.3s 出真答案；documents 端點直打回 200+32 份文件）。
共同根因有二，**都不是後端/程式邏輯**：
1. **我一個下午 redeploy ui 多次** → 使用者開著的分頁跑**舊 JS bundle** → 跟新後端對不上 → 各種怪症狀。硬重整即解。
2. **這台 dev Mac 記憶體爆**（16 容器 + Ollama 11GB + 37 分頁 + Office/會議錄製，曾剩 140MB、狂 swap）→ 分頁卡死、請求沒離開瀏覽器（log 全空可證）。已釋放：卸載閒置 ollama 模型 + 停 grafana/prometheus（恢復：`docker start staffkm-grafana staffkm-prometheus`）。

⇒ 客戶 prod **不會**像這樣（沒人一直 redeploy、機器不會這麼擠）。但「發版後分頁跑舊 JS」對**真客戶**是真風險（見 §6 TODO）。
診斷 client-side 故障的最快路：F12 → Network 看請求狀態碼（404=漏 X-Workspace-ID/沒選 workspace；pending=記憶體卡；200 但空=渲染/快取→硬重整）+ Console 紅字。

## 4. 環境關鍵事實（每次接手「對話/生成壞掉」先查這些）
- **host Ollama 必須在跑**：`default.llm=gemma4:e4b` 在主機 Ollama `http://host.docker.internal:11434`。重開機/睡眠後**不會自動起** → 沒跑時 agent LLM `Connection error`。
  - 🔑 **誤導性症狀**：citations/檢索正常（嵌入用 `embedder` 容器）但答案「回應時發生錯誤」→ **先查 host Ollama `:11434` 是否在跑**，別誤判成 RAG/程式 bug。（**已加進 CLAUDE.md 踩雷集**）
  - 啟動：`OLLAMA_HOST=0.0.0.0:11434 ollama serve`（或開 Ollama.app）。模型 `gemma4:e4b` 已下載，**勿 pull**。
- 這台 Mac 同時開很多重 App（Edge/Chrome 37 分頁/PowerPoint/Teams/會議錄製）+ 16 容器 + Ollama(11GB) → 易記憶體爆。
- 整合測試本機重跑：`docker run pgvector` + `pip install -r tests/integration/requirements.txt` + `STAFFKM_TEST_DB_URL=... pytest tests/integration/<service>`（細節見 CLAUDE.md §13 / 各 conftest）。

## 5. 安全 / 規矩（務必遵守，使用者明確要求）
- 預設**繁體中文（台灣）**溝通。
- **任何 `ollama pull` / 長下載先問**使用者。
- 不主動 `git push` 沒 review 的 commit（但使用者常說「push」就推）。
- 不 commit `.env` / `.env.production`。
- API key 只能進系統 settings 畫面，debug 只貼前後 6 字元。
- SQL：`CAST(:p AS jsonb)` 不要 `:p::jsonb`（§8）；DDL idempotent（§9）。
- 不無預警 `pnpm install` 加新 dep；不動 LoginView 中心知識圖譜插圖。

## 6. ⏭️ 下一步 TODO（新對話接手要做）：長開分頁健壯性硬化
使用者問「客戶一直開著分頁怎麼辦」。今天的痛大半是 dev 因素（見 §3），但有幾條對**真客戶**是真風險，優先做：

1. **【高 CP，先做】前端版本檢查 → 提示重新整理**（解「客戶永遠不手動重整、發版後跑舊 JS」）：
   - vite build 產 build id/hash（或讀 `index.html` 的 asset hash / 出 `version.json`）。
   - 前端在 **路由切換 + `visibilitychange`（分頁切回前景）** 時比對 → 不同 → 跳 toast「有新版本，請重新整理」（可選：偵測到 API 回版本不符時強制 reload）。
   - 注意：`apps/web/index.html` 已是 `no-store`、無 service worker（CLAUDE.md 既有事實）→ 純比對 asset hash 即可。
2. **驗證 ② token 續期**：access 8h / refresh 30天；§3 設計是 401→去重 refresh→失敗導 login。實際長閒置後送一個請求驗證會自動續、不會直接登出。
3. **③ 重新聚焦 revalidate**：`visibilitychange`/路由進入時，對關鍵清單（對話/文件/KB）重抓，避免長開分頁顯示過時資料。

實作完照慣例：整合/單元測試守 + commit + tag + `safe-redeploy.sh ui` + 更新本檔。
