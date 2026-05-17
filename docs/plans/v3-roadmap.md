# v3.0 Roadmap

> v2.x 已完成 functional parity + production-ready + B2B + dev partners。
> v3.0 是第一個 **major** 版本，按慣例可有 **breaking changes**。
> 這份規劃列盤點 + 4 主題提議 + 推薦選擇 + breaking change 清單。

## Status quo（v2.5 結束）

✅ **已成熟**
- 31 個 API 模組、6 service、25+ provider、30+ workflow nodes
- Production deploy（Caddy auto-TLS + backup）
- Auth：JWT + CAPTCHA + OIDC SSO + LDAP
- 多租戶 / RBAC / Project 抽象
- ui-kit 34 元件 + design system v2 + 3 語系
- 8 篇 user guide + API ref + CLAUDE.md

⚠️ **能跑但有債**
- **bootstrap_ddl.py** idempotent DDL —— v3 該換 alembic 真 migration
- **LegacyURLBridge** —— sunset 排在 2026-11-15，v3 拿掉
- **In-process CAPTCHA counter** —— 多 instance 部署會失準，該改 Redis
- **OIDC sub 借用 ldap_dn 欄** —— 該加正規 oidc_sub 欄
- **TypeScript SDK** —— 沒做（Python 有）
- **LINE/Teams webhook handler** —— 路徑預留但邏輯空
- **E2E test** —— plan 寫了沒實做
- **Grafana 起來但 dashboard 預設只有 1 個** —— 內容偏空

🚫 **沒做的大功能**
- 真 RWD mobile 體驗 / PWA
- 工作流 plugin SDK（讓使用者新增 node type）
- Audit log + 操作紀錄 UI
- 跨 tenant collaboration
- 即時協作編輯（多人改 KB / App）
- Voice I/O（speech in chat）

## 4 個 v3.0 主題提議

### 🅰 主題 A：Production Hardening（推薦）

**主旨**：把 v2.x 留下的「能跑但有債」逐一還清。沒 flashy feature 但堅實，後續 release 都受惠。

**範圍**：
1. **真 Alembic migrations** 取代 bootstrap_ddl —— v3 重大基礎建設
   - 一次性匯出現有 schema 為 baseline migration
   - 後續 PR 加 migration file 而非 alter bootstrap
   - 同時保留 idempotent fallback for backward compat
2. **LegacyURLBridge sunset** —— 拿掉 v1 URL rewrite
   - 所有 client 在 v2.x 期間都該遷完
   - 留 410 Gone response + 文件指向 v2 URL
3. **CAPTCHA / session → Redis** —— 多 instance ready
   - 多 gateway / agent replica 後 CAPTCHA 計數正確
   - JWT refresh blacklist 也可加進來
4. **OIDC schema 正規化** —— `oidc_sub` + `oidc_issuer` columns
5. **5 個 Grafana dashboard** —— observability-plan.md 提的 5 個 panel 真的做出來
6. **5 個 Playwright E2E** —— 從 P0 critical path
7. **Helm chart HA review** —— 確認 multi-replica session 無 sticky issue
8. **Audit log table + admin UI** —— who did what when

**Breaking changes**：
- v1 URL endpoints 移除（替代為 v2 URL，client 早該遷）
- 配置 env vars 重新整理（一些 LEGACY_* 拿掉）
- Helm chart values.yaml schema 微調

**時程**：估 2-3 週 spread over 6-8 PRs

**價值**：B2B / 企業客戶最在乎，operational confidence 大幅提升

---

### 🅱 主題 B：Plugin / Extensibility

**主旨**：把 staffKM 變成「平台」而不只是「應用」。讓第三方擴充。

**範圍**：
1. **Workflow Node Plugin SDK**
   - 讓使用者 Python package 註冊 custom node type
   - hot reload 不重啟 service
   - 範例：a SAP integration node、Slack notification node
2. **TypeScript SDK** + 自動產 type-safe API client
3. **Model Provider Plugin** —— LLM provider 加 register pattern，第三方 PR 新 model
4. **Tool Plugin** —— `/tools` 模組讓使用者註冊 HTTP / SQL / SDK 範本
5. **LINE / Teams handler** —— 真的 implement message handler，bot 跑得起來
6. **Embedding Provider Plugin** —— 不只 ollama / openai，可註冊任何
7. **Webhook subscription** —— 系統 event broadcast 給外部（new doc / chat finished / quota exceeded）

**Breaking changes**：
- Workflow node 註冊機制改（custom nodes 接 plugin API）
- Provider registry 從靜態檔變動態註冊

**時程**：估 3-4 週

**價值**：開源 / 社群 / 客戶 customization 強

---

### 🅲 主題 C：Mobile / PWA / Real-time

**主旨**：consumer-facing 體驗 → 行動端 + 即時協作。

**範圍**：
1. **PWA 安裝 + service worker** —— add-to-home-screen on phone
2. **真 RWD pass** —— 所有 view 在 < 640px 跑得順
3. **Push notification** —— 通知 task done / quota warning
4. **Offline mode**（read-only）—— cached KB browsing
5. **Multi-tab sync** —— BroadcastChannel 同步 conversation
6. **真即時協作**（WebSocket）—— 多人同時編輯 App / KB
7. **Voice I/O**（chat 講話）—— Web Speech API + STT/TTS provider
8. **Mobile-first nav 重設**

**Breaking changes**：
- ChatLayout / DashboardLayout 大改成 mobile-first
- 某些 dropdown / modal 換 bottom sheet

**時程**：估 4-5 週（RWD 重 polish 慢）

**價值**：消費者市場 / 員工日常隨手用最有感

---

### 🅳 主題 D：AI 智能體進化

**主旨**：staffKM 不只是「對話 + RAG」，是真智能體生態。

**範圍**：
1. **Multi-agent**（agent calls agent）—— 串接多個 App，類 Anthropic Computer Use
2. **真自主代理人** —— 接 tools / memories / triggers，自循環解任務
3. **Vision model 整合** —— 上傳圖片問問題、screenshot 分析
4. **Code interpreter node** —— workflow 可跑 Python（已有 sandbox 基礎）
5. **長期 task tracking** —— task 跨 session 持續
6. **Tool use 視覺化** —— chat 中顯示 tool call + result（不只 citation）
7. **Eval framework** —— measure RAG accuracy / agent success rate

**Breaking changes**：
- Conversation 訊息格式擴展（tool_use / tool_result roles）
- Workflow executor 重大改寫

**時程**：估 5-6 週（最 risky）

**價值**：差異化 / 跟 Claude / OpenAI 拼能力的本錢

---

## 推薦：**主題 A — Production Hardening**

理由：
1. **v2.x 真的可上 production，但債務拖到後面只會更難還**
   - Alembic migration 越晚換越多 schema 要 baseline
   - LegacyURLBridge 拖久了，反而怕拿掉
2. **B2B 客戶最看的是 operational maturity**，不是 flashy 功能
3. **後續主題（B/C/D）都建立在穩固基礎上**
4. **範圍可控**（2-3 週），不需 disruptive 設計改動

如果你有強烈 product vision（例：要做手機 App / 要拼 agent），可以選 B/C/D。

## 如果選 A，具體 PR 拆解

| Sprint | PR | 內容 |
|---|---|---|
| 21-A | 1 PR | 一次性匯出當前 schema → alembic baseline migration |
| 21-B | 1 PR | bootstrap_ddl 改為 fallback only（新 schema 走 alembic） |
| 21-C | 1 PR | LegacyURLBridge → 改回 410 Gone + 文件指向 v2 URL |
| 21-D | 1 PR | CAPTCHA counter → Redis；JWT blacklist 順手做 |
| 21-E | 1 PR | OIDC: 加 `oidc_sub` / `oidc_issuer` columns + migration |
| 21-F | 1 PR | Audit log table + admin /admin/audit-log view |
| 22-A | 1 PR | Playwright init + 5 P0 spec |
| 22-B | 1 PR | Grafana 5 dashboard JSON |
| 22-C | 1 PR | Helm HA review + values.yaml tidy |
| 22-D | 1 PR | v3.0 changelog + breaking changes notice + tag |

10 個 PR 跑完。

## 如果選 B/C/D 怎麼開始

可以先做「最小可驗證版本」（MVP）：

- **B**: 先做 1 個 plugin SDK proof-of-concept（Workflow Node 為例）
- **C**: 先把 ChatView + ApplicationListView 兩個 view 改 mobile-first
- **D**: 先做 multi-agent v1（簡單 agent A 呼叫 agent B）

驗證可行才推開。

## v2.x → v3.0 升級路徑

不管選什麼主題，v3.0 升級指引建議：
1. 先升 v2.5 latest（拿到所有 v2 修正）
2. 跑 backup（DR drill 級別 backup）
3. 升 v3.0
4. 跑 alembic upgrade head（取代 bootstrap）
5. 驗證 critical path（login / chat / new KB）

DB 不會壞，但 v1 URL endpoints 拿掉後外部整合需更新。

## 決策

請從 4 個主題挑：
- **A — Production Hardening**（推薦，2-3 週）
- **B — Plugin / Extensibility**（3-4 週，生態擴張）
- **C — Mobile / PWA / Real-time**（4-5 週，consumer 體驗）
- **D — AI 智能體進化**（5-6 週，能力拼）

或：跳過 v3.0，直接做 v2.6 補小 feature（例：TypeScript SDK + RWD pass）。
