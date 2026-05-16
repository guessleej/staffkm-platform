# staffKM 主要 Personas v1

> M1 收尾交付。Persona 不是行銷文案，是「**設計決策的判官**」：
> 當功能優先級拿不定主意，回到這四個人問他們會不會用、為什麼用、多久用一次。

---

## P1 ── 行政專員「依潔」（高頻使用者，~70% DAU）

- **職位**：總經理室行政專員
- **年齡 / 數位熟悉度**：32 / 一般（會用 Notion、Excel、Slack；不寫 code）
- **典型一日**：早會 9:00 → 整理會議紀錄 9:30 → 跑採購 / 簽呈 / 公文系統 10:00–15:00 → 整理週報 15:00 → 回 mail 收信 → 5:30 下班
- **痛點**
  - 各系統 SOP 散落在不同 Notion / SharePoint / PDF；新案來不知道找誰
  - 主管問「上次那個流程的決議？」沒空翻歷史紀錄
  - 表單欄位每次都填很久，常填錯被退件
- **staffKM 對她而言**
  - **主要任務**：問答（「請假流程是？」「採購單範本？」）+ workflow 自動跑「會議結論→週報」
  - **不會用的功能**：MCP / Sandbox / Workflow Manager 切換
- **判斷準則**
  - 首頁第一個 CTA 必須是「**問問題**」，不是「**建立應用**」✓
  - 對話載入 < 1.5 秒（她切回去做事的耐性）
  - 文字必須直接、不囉嗦；錯誤訊息要可以照著動

---

## P2 ── 數位轉型 PM「Kevin」（建立者，~15% DAU）

- **職位**：資訊室 / 數位轉型推動辦公室 PM
- **年齡 / 數位熟悉度**：38 / 高（懂 prompt engineering、會看 API 文件、不寫 production code）
- **典型一週**：找各部門訪談痛點、設計 workflow、給 IT 確認 model 預算、做使用者教育
- **痛點**
  - 沒有 vendor lock-in 預算 → 必須地端 LLM 走 Ollama
  - 不同部門有不同 RBAC 需求 → workspace + role 必不可少
  - 上面盯成本 → 必須能看 token / cost dashboard
- **staffKM 對他而言**
  - **主要任務**：建立 application、設定 knowledge base、設計 workflow、切 model provider、調 quota
  - **重度使用**：admin/usage、application 設定頁、workflow 編輯器、model providers
- **判斷準則**
  - Workflow 編輯器要能 **undo / 複製貼上 / Cmd+S**（M2 收尾已交付 ✓）
  - Usage dashboard 要能看到 per-application breakdown（M3 收尾 v1 還只有 workspace 級；可放 backlog）
  - Provider 切換要有 dropdown + 預設值（M3 中段已交付 ✓）

---

## P3 ── IT 管理者「家豪」（守門員，~5% DAU 但每次都是大事）

- **職位**：資訊室主任 / DevOps
- **年齡 / 數位熟悉度**：45 / 中高（K8s、PostgreSQL、Linux；不碰前端）
- **典型一日**：監看系統健康、處理稽核請求、回應安全事件、批准 quota
- **痛點**
  - 老闆問「上個月 LLM 花了多少？哪個部門用最多？」要立刻回得出來
  - 稽核時被問「資料外洩怎麼擋」要有具體答案（多租戶 / sandbox / RBAC）
  - 不希望被 vendor 鎖（pricing / SLA / 離岸法規）
- **staffKM 對他而言**
  - **主要任務**：監看用量、設定 workspace quota、檢視 audit log、控管 API key
  - **重度使用**：admin/usage、admin/users、API key 管理、RFC 文件
- **判斷準則**
  - Quota 必須能 hard-cap（超額直接 429，不能只是 warning）✓ 已交付
  - 所有跨服務呼叫都要有 log（M3 收尾的 usage log 已涵蓋 LLM；MCP 等待 M4 中段）
  - 系統文件齊全（RFC + brand + ux + ddl）

---

## P4 ── 部門主管「淑芬」（檢視者，~10% 偶爾用）

- **職位**：部門經理 / 處長
- **年齡 / 數位熟悉度**：50 / 中（會用 PowerPoint、Outlook、Line；對 AI 既期待又警戒）
- **典型一日**：跑會議、看報表、批簽呈、跟客戶 / 上級溝通
- **痛點**
  - 想知道「**部門的知識**」有沒有被好好用、有沒有風險
  - 不想學新系統；介面要像 LINE / 微信一樣自然
  - 怕個資外洩、怕 AI 亂講
- **staffKM 對她而言**
  - **主要任務**：偶爾打開看部門 application 的對話記錄、查週報 / 月報
  - **不會用的功能**：所有 admin / workflow / API
- **判斷準則**
  - 預設首頁 = `/chat`（不是 dashboard）✓
  - 對話旁有 citation 來源，可點開原文（已交付）
  - 沒人教她也能 5 分鐘上手 → onboarding tip / empty state copy 要清楚

---

## 設計優先序映射

| 設計決策                            | 主要 persona | 次要 persona |
| ----------------------------------- | ------------ | ------------ |
| 對話為中心 layout                   | 依潔 / 淑芬   | Kevin        |
| 地端 LLM 預設                       | 家豪          | Kevin        |
| Workflow 編輯器升級                 | Kevin         | —            |
| Usage dashboard + Quota             | 家豪          | Kevin        |
| Multi-tenant + RBAC                | 家豪          | Kevin        |
| Brand sober 不浮誇                  | 全體          | —            |
| 高密度卡片（claude.ai 對標）         | 依潔 / Kevin  | —            |

---

## 不在這四個 persona 內的人

- 軟體工程師、API integrator → 走 SDK / OpenAPI（M5 規劃）
- 外部承包商 → 透過 share link（D-4 已交付）
- 終端客戶 → 不直接使用 staffKM；由部門主管/專員代為查詢
