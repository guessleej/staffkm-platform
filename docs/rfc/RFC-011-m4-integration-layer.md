# RFC-011 — M4 整合層 / 對外接面

| 項目      | 內容                                           |
| --------- | ---------------------------------------------- |
| 狀態      | Draft（M4 啟動）                              |
| 提案日期  | 2026-05-16                                     |
| 對應里程碑 | M4 — 進階能力 GA                              |
| 相關 PR   | feat/m4a~e（媒體 / 記憶 / 觸發 / MCP / 本 RFC） |

## 1. 動機

M4 把 staffKM 從「應用 + 知識庫 + workflow」推進到「**可被外界事件驅動、可記住、會看圖會說話、可呼叫外部 MCP 工具**」的智能代理層。
這層的關鍵不是「再加幾個 node」，而是把以下四件事用一致 / 安全 / 多租戶隔離的介面表達出來：

1. 多媒體（image / TTS / STT）— 已啟動（PR #93）
2. 長期記憶（per user / app / team）— 已啟動（PR #94）
3. 事件觸發（cron / interval / webhook）— 已啟動（PR #95）
4. MCP Hub（外部工具註冊與呼叫）— 已啟動（PR #96）

本 RFC 定義它們之間的「整合層」契約：誰呼叫誰、共用什麼欄位、如何在 workflow 中組合。

## 2. 整合視角

```
                   ┌─────────────────┐
                   │   Application   │  ← User 啟動點
                   └────────┬────────┘
                            │
                ┌───────────┼────────────┐
                ▼           ▼            ▼
         ┌──────────┐ ┌──────────┐ ┌──────────┐
         │ Workflow │ │ Memory   │ │ Triggers │
         │ Executor │ │ Store    │ │ (cron)   │
         └─────┬────┘ └────┬─────┘ └────┬─────┘
               │           │             │
   ┌───────────┼───┬───────┼─────┐       │
   ▼           ▼   ▼       ▼     ▼       │
 ┌────┐ ┌────────┐ ┌─────┐ ┌─────┐       │
 │LLM │ │ Media  │ │ MCP │ │Shell│       │
 │Adp │ │  Adp   │ │ Hub │ │Sbx  │       │
 └────┘ └────────┘ └─────┘ └─────┘       │
                                          ▼
                              ┌─────────────────────┐
                              │  trigger_worker     │
                              │  (60s polling loop) │
                              └─────────────────────┘
```

## 3. 共用契約

### 3.1 多租戶隔離

所有 M4 表都帶 `workspace_id`，沿用既有 `WorkspaceScopedQuery` 模式 + RBAC：
- 讀：`require_member`
- 寫：`require_writer`（editor 以上）
- Admin-only：`require_admin`（quota / system）

### 3.2 SSE 事件命名

統一前綴 + verb：
- `<noun>_<verb>` 形式：`mcp_call_start`、`memory_recall_done`、`trigger_queued`
- 既有：`token / citations / done / error / retry / parallel_* / batch_* / shell_*`

### 3.3 觀測與計帳

- 一切「跨服務 / 跨網路」呼叫都會經 `record_usage()` 寫一筆 log
  - LLM → `model_usage_logs`
  - Media → `model_usage_logs`（model='dall-e-3' / 'whisper-1' / ...）
  - MCP → 後續 PR 加 `mcp_call_logs`（M4 中段）
- 共用 `latency_ms / status / error / workspace_id / user_id / application_id` 欄位

## 4. 在 workflow 中組合的標準 pattern

### 4.1 Trigger → Workflow → Memory

```yaml
# 1. event_triggers: cron */15 * * * *  → fire workflow
# 2. workflow nodes:
- start
- variable:    bind { topic: "AI 新聞" }
- http_request: fetch RSS
- llm:          summarize
- memory_save:  scope=user, content={{llm_response}}, importance=7   # M4 中段新節點
- email:        digest to creator
```

### 4.2 Workflow + MCP Tool

```yaml
- start
- mcp_call:                          # M4 中段新節點
    server_id: ${slack_mcp}
    tool: send_message
    arguments: { channel: "#ai", text: "{{llm_response}}" }
```

### 4.3 Memory recall（語意檢索）

```yaml
- start
- memory_search:                     # M4 中段新節點
    query: "{{user_input}}"
    scope: user
    top_k: 5
    output_variable: relevant_memories
- llm:                                # llm system prompt 帶 {{relevant_memories}}
```

## 5. 範圍切割

| 階段       | 內容                                                                  |
| ---------- | --------------------------------------------------------------------- |
| M4 啟動（已合：#93~96 + 本 RFC） | DDL + API + worker scaffold + 客戶端                |
| M4 中段    | workflow 新節點：`memory_save / memory_search / mcp_call`             |
|            | trigger dispatcher：從 queued runs 取出來 cross-call chat endpoint     |
|            | media providers 接入 workflow `_exec_*`（image/tts/stt 走 registry）  |
| M4 收尾    | UI：MCP Hub / Memory / Triggers 三件管理頁                            |
|            | embedding-based memory recall（取代純全文）                            |

## 6. 風險

- **trigger_worker 多副本**：目前 lifespan 啟動一個 task；多 replica 部署會重複觸發。
  M4 中段加 `SELECT … FOR UPDATE SKIP LOCKED` 或 advisory lock，保證單一觸發。
- **MCP server URL outbound**：使用者可填任意 URL → SSRF 風險。
  M4 中段加 URL allow-list（per workspace）+ outbound network policy（容器層）。
- **Memory 規模**：long_term_memories 沒有上限 → 一個 workspace 可灌爆。
  M4 收尾加 per-workspace memory cap（沿用 quota 框架）。
- **多媒體成本暴衝**：DALL-E 一張 $0.04，TTS 1M tokens 約 $15 — 需納入 quota cost。

## 7. 驗收標準（M4 GA Definition of Done）

- [ ] 所有 4 件子系統都有對應 management UI（Memory / Trigger / MCP）
- [ ] workflow 內可用 `memory_search` / `mcp_call` 節點
- [ ] cron trigger 可實際自動跑 workflow（dispatcher 就位）
- [ ] media providers 透過 registry 切換（DALL-E / Stability）
- [ ] 多副本下 trigger 不重複觸發
- [ ] SSRF allow-list 上鉤
