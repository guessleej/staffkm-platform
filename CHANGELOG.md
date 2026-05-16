# Changelog

依 [Keep a Changelog](https://keepachangelog.com/) 與 SemVer。

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
