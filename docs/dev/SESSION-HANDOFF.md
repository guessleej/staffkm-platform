# staffKM — Session 接手交接（貼到新對話用）

> 給新對話的 Claude：先讀 repo 根目錄 `CLAUDE.md`（專案記憶，含設計決策/踩雷集/tag 表），
> 再讀本檔補「最近這輪做了什麼 + 一個還沒結案的問題」。本檔位置：`docs/dev/SESSION-HANDOFF.md`。

## 0. 專案一句話
staffKM — 企業 AI 知識管理平台，Monorepo（apps/web Vue3 + services/* FastAPI + PostgreSQL/pgvector + 本機 Ollama 預設）。
Repo：`github.com/guessleej/staffkm-platform`，工作分支 `main`。

## 1. 這輪（v5.12.6 → v5.12.24）做了什麼 —「測試深化 + 生產硬化」

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

**chat deep-link 修（v5.12.24，已部署）**：
- 問題：`/chat?conv=<id>` 直接開/重整顯示空白。根因：`ChatView.selectFromRoute` 只在記憶體清單找對話、無 by-id 退路；後端也沒有單一對話詳情端點。
- 修：後端加 `GET /chat/conversations/{id}`（回 application_id/scenario_id/kb_ids + ownership）；前端 store `fetchConversationById` + `selectFromRoute` fallback。+3 整合測試。

## 2. Git / 部署狀態
- `main` 已 push 到 `v5.12.24`（與 origin 同步）。
- **已重新部署**：`ui` + `chat`（v5.12.24 的 deep-link 修已 live）。
- **未重新部署**：`agent`（仍是舊 code，Up 42h）— 所以 API key 單一來源(v5.12.11)等 agent 改動**還沒 live**，但不影響運行（舊 decrypt_secret 仍在舊容器內、行為相容）。
- 重新部署指令：`./tools/scripts/safe-redeploy.sh <service...>`（如 `ui chat`）。

## 3. ⚠️ 還沒結案：chat 對話「回不出來 / 回應時發生錯誤」
**目前結論：後端是好的，問題在前端分頁狀態 +（曾經的）記憶體爆。**

排查到的事實：
- 後端用真實路徑實測（chat→agent→應用對話→gemma4）→ **200、0.3~0.6 秒串流出真答案**。
- 使用者「回不出來」那次：nginx/gateway/chat/agent log **全空** → 請求**根本沒離開瀏覽器**。
- 早一陣子 host 記憶體爆（剩 140MB、狂 swap）→ 瀏覽器分頁卡死；後來自己回穩（9.5GB free）。
- 我已釋放記憶體：卸載閒置 ollama 模型（下次聊天重載 ~10s）+ 停 grafana/prometheus 容器（對 App 零影響，要恢復：`docker start staffkm-grafana staffkm-prometheus`）。

**下一步（給使用者 / 新對話接手）**：
1. 在分頁 **Cmd+Shift+R 硬重整** → 重送訊息（第一則因 gemma4 重載會慢 ~10s）。
2. 還不行 → F12 → Network 看 `.../messages/stream` 請求是否出現、狀態碼；Console 有無紅錯。

## 4. 環境關鍵事實（每次接手「對話/生成壞掉」先查這些）
- **host Ollama 必須在跑**：`default.llm=gemma4:e4b` 在主機 Ollama `http://host.docker.internal:11434`。重開機/睡眠後**不會自動起** → 沒跑時 agent LLM `Connection error`。
  - 🔑 **誤導性症狀**：citations/檢索正常（嵌入用 `embedder` 容器）但答案「回應時發生錯誤」→ **先查 host Ollama `:11434` 是否在跑**，別誤判成 RAG/程式 bug。（已誤導兩次，待補進 CLAUDE.md 踩雷集 — 使用者尚未確認是否要加）
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
