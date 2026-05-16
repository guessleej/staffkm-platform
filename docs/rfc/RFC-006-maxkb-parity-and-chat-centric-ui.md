# RFC-006：MaxKB 功能對齊 + 對話為中心的 UI 改造

| 欄位 | 內容 |
|------|------|
| 編號 | RFC-006 |
| 提案者 | @leeweiye |
| 狀態 | Draft |
| 建立日期 | 2026-05-16 |
| 最後更新 | 2026-05-16 |
| Reviewers | @arch @lead-be @lead-fe @pmp |
| 取代 / 被取代 | 無 |

---

## 1. 摘要（Summary）

把 v2 的產品定位從「對齊 MaxKB」升級為「**MaxKB 功能 parity + 對話為中心的 UI**」。本 RFC 透過實地探勘 MaxKB v2 介面（http://localhost:8080）盤點功能差距，並提出 UI 改造方向（對標 claude.ai 的單欄對話 + 左收納抽屜結構），最後給出新 backlog 與 M1~M5 重排建議。

範圍邊界（依 2026-05-16 共識）：
- **Feature parity（功能對齊），不抵拼畫面**
- 不複製 MaxKB 的 enterprise tier「升級」概念（社區版範圍）

## 2. 動機（Motivation）

### 2.1 原 22 週計畫的盲點
原計畫假設「對齊 MaxKB」意指主要 backlog 條目對齊，但實地探勘後發現 MaxKB 有 3 個**模組層級**的概念未在 backlog 出現：

1. **獨立的 Tool 模組**（v2 只把 MCP 當作 workflow node，沒當成可獨立管理的資源）
2. **Skills**（可重用的 prompt 技能，跨 Application 共享）
3. **Template Center / Tool Store**（社區市場模式，含下載統計）

### 2.2 UI 層的 mismatch
PR #45 把工具列移到水平頂部，是「管理後台」風格。MaxKB 走的也是傳統「上導覽 + 左列表 + 中內容」三欄結構。但本案最終使用者主要任務是**對話與查詢知識**，介面應對標 claude.ai 的「對話為主、其他為輔」結構，否則進入即見「空狀態 + 創建按鈕」對 RAG 助理使用體驗不友善。

## 3. MaxKB 功能盤點（實地探勘）

### 3.1 頂部結構
4 大模組：**智能體 / 知識庫 / 工具 / 模型**。右側：升級按鈕、wrench、GitHub 連結、螢幕圖示、help、user avatar。每個模組進入後皆有共同 pattern：

- 左側可收合 sidebar（搜尋 + 排序 + Folder 樹）
- 中央內容區：上方有「名稱 filter / 搜尋 / 批量選擇 / 模板中心或商店 / 創建」工具列
- 「創建」永遠是右上 primary button，下拉展示**該模組所有可建立的子類型**

### 3.2 智能體（Application Builder）
- **4 種建立方式**：簡易（表單）/ 進階編（低代碼拖拉）/ 匯入 / 添加文件夾
- **模板中心**：社區模板市集，含下載次數，內含 CRM 系列、長文寫作、知識庫問答、發票識別、SQLBot、報價單、戶籍政策、學生自測、案例收集、數據分析、合同審核、官網翻譯⋯⋯約 12+ 模板可見

### 3.3 知識庫
- **5 種建立方式**：通用（上傳本地檔）/ Web（同步網站）/ 工作流（自定義流程建構）/ 匯入 / 添加文件夾
- 知識庫卡片顯示文件數 + 字符量統計

### 3.4 工具
- **7 種建立方式**：工具 / 工作流 / Skills / MCP / 數據源 / 匯入 / 添加文件夾
- **工具商店**：類似模板中心的社區市集（獨立於模板中心）

### 3.5 模型
- **20+ 供應商**：OpenAI / Anthropic / Azure OpenAI / Amazon Bedrock / Gemini / DeepSeek / Kimi / Ollama / vLLM / MiniMax / SiliconFlow / Regolo / Docker AI / Xorbits Inference / 阿里雲百鍊 / 騰訊雲 / 騰訊混元 / 火山引擎 / 千帆 / 訊飛星火 / 智譜 AI / 本地模型⋯⋯
- 左側分 **公有模型 / 私有模型**（暗示帳戶層級共享 vs 個人）
- 右上 filter 可依模型類型篩選（LLM / Embedding / Rerank / STT / TTS 等）

### 3.6 跨模組通用模式
- **Folder 樹**：所有模組都有資料夾組織能力，不只是 KB
- **批量選擇**：所有模組都有批量操作工具列
- **匯入 / 匯出**：所有模組都支援 import（暗示有匯出 zip / 備份能力）
- **i18n**：右上有語系切換（已見繁體中文 / 應該還有簡中、英、其他）
- **CAPTCHA**：登入有圖像驗證碼

## 4. claude.ai UI 對標（設計模式描述）

claude.ai/new 的設計模式（不涉具體內容複製）：

- **單欄聚焦**：進入即「對話框 + 訊息流」，沒有多餘的頂部 nav
- **左側收納抽屜**：可摺疊的歷史對話列表，依日期分群（今天 / 昨天 / 過去 7 天等）
- **頂部極簡**：只留 model picker 與當前對話標題
- **訊息卡片極簡**：無頭像、僅文字 + code block；引用以 footnote 方式呈現
- **底部輸入區**：sticky 在頁面底部；附件、Project 內容指示 inline 顯示
- **右側 Artifact pane**：需要時 slide-in，展示程式碼 / 文件 / 互動預覽
- **Project 抽屜**：把對話 + 檔案 + 自訂指令打包為一個專案空間
- **配色**：高對比、極少階層，dark mode 為純黑底，留白寬鬆
- **字體**：系統 sans + 部分 serif accent

## 5. Gap 矩陣

### 5.1 功能層面

| MaxKB 模組 / 概念 | v2 backlog 現況 | 差距處理 |
|---|---|---|
| Folder 樹（跨模組） | M1 Folder（僅 KB） | **EXPAND**：所有模組通用 |
| Web KB 同步 | 無 | **NEW**：Web crawl + 增量同步 |
| 工作流知識庫 | 無 | **NEW**：用 workflow 結果建 KB |
| Application 模板中心 | 無 | **NEW**：社區模板市集 + 下載統計 |
| Tool 模組（獨立） | 僅 MCPTool node | **UPGRADE**：升格為一級模組 |
| Skills | 無 | **NEW**：可重用 prompt 技能 |
| 數據源（Data Source） | 無 | **NEW**：DB / API 連接器 |
| 工具商店 | 無 | **NEW**：tool 社區市集 |
| 公有 / 私有 模型分軌 | 無 | **NEW**：跨 workspace 共享 vs 私有 |
| 20+ Model Provider | M3 (3 個目前) | **EXPAND**：補 16+ |
| Import / Export | 無 | **NEW**：zip 匯入匯出（KB / App / Tool） |
| 批量選擇 toolbar | 無 | **NEW**：跨模組 UI 原語 |
| i18n（繁中 / 簡中 / 英文） | 無 | **NEW**：i18n 框架 + 字典 |
| CAPTCHA 登入 | 無 | **NEW**：安全選項（評估後決定） |
| 升級 / Edition tier | 不在範圍 | **SKIP**（社區版） |

### 5.2 UI 層面（對標 claude.ai）

| 設計模式 | 現況 (PR #45 後) | 改造方向 |
|---|---|---|
| 單欄對話為中心 | 多區頁面 + 水平頂部導覽 | **REWRITE**：對話 = 預設首頁 |
| 左側可收納對話歷史 + 日期分群 | 無 | **NEW**：ChatHistoryDrawer |
| 頂部極簡 | 4 模組頂部導覽 | **REDESIGN**：對話內頁只留 model 顯示 + 標題 |
| 訊息無頭像 | 已去 emoji，仍有圓 chip | **REMOVE**：剩 chip 全砍 |
| 右側 Artifact pane | 無 | **NEW**：workflow / document / chart 預覽欄 |
| Project 概念 | 無 | **NEW**：把 application + KB + chat 打包為 project |
| Dark mode 純黑、寬鬆留白 | 已有 dark mode 但配色階層多 | **SIMPLIFY**：降階層數、加大留白 |

## 6. 新 Backlog 條目

依優先級分群：

### P0（M1 範圍內補）
1. Folder 樹通用化（橫跨 Application / KB / Tool / Model）
2. 批量選擇 toolbar UI 原語
3. i18n 框架 + 繁中字典

### P1（M2 範圍內補）
4. Web KB 同步（crawler + 增量）
5. 工作流知識庫
6. Application 模板中心 + 種子模板
7. Application / KB / Tool import-export（zip 格式）

### P2（M3 補強）
8. Skills 模組（reusable prompt skills）
9. 公有 / 私有模型分軌（多 workspace 共享機制）
10. 補齊 16+ Model Provider

### P3（M4 範圍內）
11. Tool 模組獨立化（從 MCP node 升格）
12. 數據源模組（DB / API 連接器）
13. 工具商店
14. MCP Hub（已在原 M4）

### UI 改造（跨 M1~M3，建議 M1 收尾啟動）
15. ChatView 重做：claude.ai-style 單欄
16. ChatHistoryDrawer（左收納 + 日期分群）
17. ArtifactPane（右側 slide-in 預覽）
18. Project 抽象層
19. 簡化 dark mode 配色階層
20. 移除剩餘訊息頭像 chip

## 7. M1~M5 重排建議

原 22 週計畫需擴張為 **28~30 週**（+6~8 週）才能涵蓋 parity。

| 里程碑 | 原範圍 | 新範圍（含 RFC-006） | 預估天數變動 |
|---|---|---|---|
| M1 | 多租戶 + Folder（KB）+ 設計系統 | + Folder 通用化、批量 toolbar、i18n 框架、ChatView 重做、ChatHistoryDrawer | +10d |
| M2 | Workflow Engine v2 + 35+ node + 5 Manager + Sandbox | + Web KB 同步、工作流 KB、Application 模板中心、Import/Export | +12d |
| M3 | Provider 抽象 + 20+ Provider + Token 計帳 | + Skills 模組、公私模型分軌、ArtifactPane | +10d |
| M4 | 多媒體節點 + Memory + Trigger + MCP Hub | + Tool 模組獨立、數據源、工具商店、Project 抽象 | +8d |
| M5 | Nuxt 遷移 + 觀測 + K8s + SDK + 文件 + UAT | 不變 | — |

**新增的 20 個 backlog 條目**已可注入 GitHub Project（第 8 節提供腳本）。

## 8. 後續行動

1. ✅ 完成本 RFC（A3）
2. ⏳ A4：把 20 個新 backlog 條目注入 GitHub Project，並重排 M1~M5
3. ⏳ Phase B：先做 ChatView 重做（最小可驗收的 UI 對標 spike）
4. ⏳ Phase B：補 M1 P0 三項（Folder 通用化、批量 toolbar、i18n）
5. ⏳ Phase C：依新 backlog 順序推進

## 9. 風險與決策待確認

| 議題 | 選項 | 建議 |
|---|---|---|
| Project 抽象與既有 Workspace 是否合併 | (a) Workspace = Project；(b) 一個 Workspace 多個 Project | (b) 較貼近 MaxKB & claude.ai 使用模式 |
| 模板中心要不要做社區後端 | (a) 純前端 seed 模板；(b) 接 GitHub repo；(c) 自建 hub | (a) 開始，視採用率升級 |
| Web KB 增量同步頻率 | (a) 手動觸發；(b) cron；(c) webhook | (a)+(b) 同時提供 |
| CAPTCHA 是否做 | (a) 不做；(b) 做選項 | (b) 選項開關 |
| 升級 / Edition tier | (a) 完全不做；(b) 預留 hook | (a) 社區版唯一 |

## 10. 不在本 RFC 範圍

- 像素級複製 MaxKB UI
- 重現 MaxKB 原始程式碼（GPL-3.0 來源）— 本案以**功能與 UX 模式對齊**為原則，獨立實作
