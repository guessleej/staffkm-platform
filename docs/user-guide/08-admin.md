# 管理介面

> 只有 `admin` role 看得到頂 nav 右側的「使用者 / 模型 / 設定」。
> 其餘還有「進階」icons 區（技能 / 工具 / 資料來源 / MCP / 排程 / 長期記憶）所有 writer 都可用。

## 使用者管理 `/admin/users`

- 列出所有 user（username / display_name / email / roles / status）
- 新增 user：手動帳密、或從 LDAP / OIDC 自動 sync
- 編輯：改 role / 啟停 / reset password
- 4 階 role：owner / admin / editor / viewer
- 注意：刪 user 不會刪該 user 建的 KB / App（保留）

## 模型供應商 `/admin/models`

每個 workspace 可註冊多個 model provider：
- **Ollama**（地端，預設）— 無需 API key
- **OpenAI / Anthropic / Gemini / Cohere / Bedrock / Vertex AI / MiniMax** — 各家自己 key
- **OpenAI-compatible** — 任意 endpoint（含自架 vLLM）
- 每個 provider 可註冊多個 model（LLM / Embedding / Reranker）
- 預設 model 給新 App 用

## Token 用量 `/admin/usage`

- 本月卡片：總 tokens / 成本 USD / 請求數
- 最近 50 筆 usage log（時間 / app / provider / tokens / cost / latency / status）
- **Quota 設定**：月 token cap + 月成本 cap
  - 留空 = 無限制
  - 超過 → 新請求回 429（含明確錯誤訊息）

## 設定 `/admin/system`

- workspace 名稱 / slug / 說明
- LLM / embedding 預設值
- 整合（LDAP / OIDC / LINE / Teams）
- 備份狀態（顯示上次成功時間）

## 進階模組（icon 區）

| icon | 路徑 | 內容 |
|---|---|---|
| 🔑 | /skills | 可重用 prompt 技能（給 App / Workflow 引用）|
| ⚙️ | /tools | 工作流可用工具（http_request / SQL / 自訂）|
| 🗄 | /data-sources | 外部資料連接器（DB / API）|
| 🔗 | /mcp/servers | Model Context Protocol 工具伺服器 |
| 🔄 | /triggers | 排程觸發（interval / cron / webhook）|
| ℹ️ | /memories | 長期記憶（user / app / team 三層 scope）|

## Project 管理 `/projects`

任何 writer 都可建 Project；admin 額外可看所有 workspace 內的 Project。
詳見 [05-projects.md](./05-projects.md)。

## 備份 / 還原

不是 UI 操作，是 server-side script。詳見 `docs/deploy/backup-restore.md`。
admin 可在「設定」頁看「上次備份成功時間」健康指標（v2.5 加）。

## 監控

- Grafana：`https://staffkm.example.com/grafana/`（admin basic-auth）
- Prometheus：內部 only（`docker exec staffkm-prometheus ...`）
- 5 個 starter dashboard：流量 / LLM 用量 / 錯誤率 / 延遲分佈 / Celery queue

---

下一篇：[99-faq.md](./99-faq.md)
