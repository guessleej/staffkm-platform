# 建立應用

3 條路徑，建議從「模板」起步。

## A. 從模板（最快）

1. `/applications` → 「✨ 從模板建立」
2. 分類 chip 篩選（全部 / 知識問答 / 客服 / 文件 / SQL / 訓練 / 翻譯 / 我的模板）
3. 每張卡片有兩顆按鈕：
   - **🎮 立即試用** — 開全屏 chat，跟模板對話試效果，不會建 App、不計 usage
   - **使用此模板** — prefill 表單，改名 + 選 KB → 建立

### 6 個內建模板

| 模板 | 適用場景 |
|---|---|
| 🧠 內部知識問答 | 規章 / SOP / 福利自助查 |
| 💬 客服 FAQ 助理 | 對外 7×24 諮詢 |
| 📝 合約審閱助理 | 標風險條款 |
| 📊 SQL 查詢助理 | schema 餵 KB → 自然語言出 SQL |
| 🎓 內訓陪練教練 | 出題 + 回饋 |
| 🌏 文件翻譯助理 | 中英對譯，保留格式 |

## B. 從空白

`/applications` → 「+ 新增應用」 → 填：
- 名稱 / 描述
- 開場白
- System prompt（給 LLM 的「人格 + 規則」說明）
- 範例問題（quick-start chips）
- 選哪些 KB 進 RAG
- LLM model（從 Model Hub 選；admin 在「模型」分頁配）
- Reranker（選填，提升 RAG 命中精度）

## C. Workflow 應用（進階）

不是「prompt」而是「節點圖」，給多步驟流程用。

`/applications` → 新增 → type = `workflow`：
- 進編輯器，drag 節點到 canvas
- 連線（start → ... → answer）
- 節點種類：LLM / knowledge_retrieval / condition / loop / http_request / form / image / speech / MCP tool / ...（30+）
- 「測試」按鈕線上跑
- 「節點版本」抽屜可快照 + 回滾

詳細：`docs/dev/workflow-nodes.md`（待）

## D. 把建好的應用存成模板

任一 App 卡片 hover → 「存模板」 → 取名 + emoji → 進你 workspace 的「我的模板」
- 下次「✨ 從模板建立」會看到自訂模板區
- 可刪 / 跨 workspace 分享（待 v2.5）

## E. 對外分享 App

App 卡片 → 「分享」icon → 拿到 public URL（`/share/{appId}`）
- 必須先把 App 設 `is_public = true`
- 分享連結拿到沒登入 staffKM 也能用
- 可包成 embeddable widget 嵌任何網站 — 見 [07-embed-widget.md](./07-embed-widget.md)

## F. API 呼叫

App 卡片 → 「API Key」icon →:
- 生 API key
- 看程式碼範例（curl / Python / JS）
- 對應 endpoint 是 `POST /api/v1/applications/{id}/chat`（用 API key bearer）

---

下一篇：[05-projects.md](./05-projects.md) — Project 抽象
