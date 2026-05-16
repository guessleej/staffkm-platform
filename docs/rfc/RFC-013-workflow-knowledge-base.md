# RFC-013 — Workflow Knowledge Base（KB ETL Workflow）

| 項目      | 內容                                       |
| --------- | ------------------------------------------ |
| 狀態      | Draft（M5 GA 之後；本 PR 落地 scaffold）   |
| 提案日期  | 2026-05-17                                 |
| 對應里程碑 | v2.1 — MaxKB Parity 收尾                  |
| 相關 PR   | feat/kb5-workflow-kb                       |

## 1. 動機

MaxKB 截圖中「**轉換為工作流知識庫**」是一種完全不同的 KB 形式：
- 來源不是手動上傳檔案，而是「**一條 workflow**」每次跑完產出 chunks
- 適合場景：
  - 每天從外部 API 拉新聞 → 切片 → 寫進 KB
  - 監聽某個 webhook 把 issue / ticket 寫成段落
  - 跑 ETL 從 DB 取資料 → 摘要 → 寫進 KB

對標既有 staffKM 元件：
- **Workflow Engine v2**（M2）已有 30+ node types
- **Event Triggers**（M4）已能定期 fire workflow
- **KB documents / paragraphs**（M1）已有 chunk + embedding pipeline
- **Memory store**（M4）已有寫入 / 全文搜尋介面

把這四件接起來 = workflow KB。

## 2. 概念

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  Event Trigger   │───►│ Workflow Engine  │───►│ kb_writer node   │───┐
│  (cron / webhook)│    │ (existing 30+    │    │ (new in this RFC)│   │
└──────────────────┘    │  node types)     │    └──────────────────┘   │
                        └──────────────────┘                            ▼
                                                            ┌──────────────────┐
                                                            │ documents +      │
                                                            │ paragraphs +     │
                                                            │ embeddings       │
                                                            │ (existing tables)│
                                                            └──────────────────┘
```

## 3. 新元件

### 3.1 KB 標記 `source_type`

```sql
ALTER TABLE knowledge_bases
  ADD COLUMN source_type VARCHAR(16) NOT NULL DEFAULT 'manual';
  -- 'manual'   既有：人工上傳檔案
  -- 'workflow' 新：由 workflow 寫入
ALTER TABLE knowledge_bases
  ADD COLUMN source_workflow_id UUID;  -- workflow_kb 才填
```

### 3.2 新 workflow node：`kb_writer`

config：
```yaml
node_type: kb_writer
config:
  kb_id: <target KB UUID>                    # 必填；驗證 == source_workflow_id 對應的 KB
  content_variable: "{{summary}}"            # 從 context 取要寫入的純文字
  title_variable: "{{title}}"                 # 段落標題（可選）
  source_variable: "{{source_url}}"           # 寫到 paragraph.meta.source
  chunking: "auto" | "single" | "paragraph"   # single = 整段成一個 paragraph；其他走 KB 設定
  upsert_key: "{{ticket_id}}"                 # 如指定，先 delete 舊 paragraph + insert
```

執行步驟：
1. 驗證 `kb_id == source_workflow_id` 對應的 KB（防止跨 KB 污染）
2. 透過 knowledge service `POST /knowledge/documents/{kb_id}/inline-write` 寫入
   - 這 endpoint 是本 RFC 新增（避免走檔案 upload 流程）
3. 等 embedding 完成才回（或非同步；config 可選）

### 3.3 新 knowledge endpoint：inline-write

```
POST /knowledge/documents/{kb_id}/inline-write
Body: {
  title: str | null,
  content: str,                  # 已是「乾淨文字」，由 workflow 預處理
  source: str | null,            # 寫入 paragraph.meta.source
  chunking: "single" | "auto" | "paragraph",
  upsert_key: str | null,        # 命中時先刪同 source / upsert_key 的舊 paragraph
}
```

寫入路徑：
- 建一個 `Document(name=upsert_key or now-iso, file_type='inline', file_size=len(bytes))`
- 直接 chunk 並寫 paragraphs；走既有 `paragraph_embeddings` upsert
- 不入 minio（純文字 KB 不需要原檔）

## 4. UI

**KB 列表卡片**：
- 加 badge：`手動` / `工作流`
- 「轉換為工作流知識庫」按鈕（**不可撤回**確認）
- 工作流 KB 點進去 → 顯示「來源 workflow」+「最近執行紀錄」（從 event_trigger_runs 拉）

**Workflow editor**：
- palette 新增 `kb_writer` 節點
- 節點設定面板：dropdown 選 kb_id（只列當前 user 可寫的工作流 KB）

## 5. 範圍切割

| 階段        | 內容                                                            |
| ----------- | --------------------------------------------------------------- |
| **本 PR**   | DDL + RFC + workflow_kb_setup endpoint（標記 KB 為 workflow 型） |
| v2.1 中段   | `inline-write` endpoint + `kb_writer` workflow node            |
| v2.1 收尾   | UI：「轉換」按鈕、palette node、執行紀錄整合到 KB 詳情頁         |
| v2.2        | 進階：條件式去重、定時 reindex、來源系統 webhook 一鍵接 (Github / Jira) |

## 6. 風險

- **寫入暴衝**：trigger 設 1 分鐘就 fire 一次 → KB 段落爆增；
  防護：per-trigger 預設 rate-limit + KB-level row count cap（後續加）
- **upsert_key 重複**：兩 workflow 互相干擾；
  防護：upsert_key 預設只在「同 workflow_id」內生效，跨 workflow 不會誤刪
- **embedding 成本**：每次 trigger 都重 embedding；
  防護：content hash 比對，相同內容跳過 embedding 直接 reuse

## 7. 取消已轉換的 KB 規則

「轉換後不可撤回」是**設計選擇**（MaxKB 也如此）：
- 工作流 KB 的 documents 名稱是 auto-generated，難以還原成手動上傳的語意
- 若需要逆轉：先匯出 ZIP，再建一個手動 KB 從 ZIP 還原

## 8. 驗收（v2.1 收尾）

- [ ] 一個 cron trigger 每天 9:00 跑 → 從 RSS 拉新聞 → kb_writer 寫進 workflow KB
- [ ] application 對話可問「今天有什麼新聞」並引用 workflow KB 的段落
- [ ] KB 詳情頁顯示「來源 workflow」+「最近 7 次 trigger run」
- [ ] 重複 upsert_key 會更新而非堆疊
