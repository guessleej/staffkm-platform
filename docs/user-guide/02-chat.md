# 跟 AI 對話

## 進入

點頂 nav「對話」 → `/chat`。

## 基本操作

1. **打字** — 下方輸入框，Enter 送出
2. **新對話** — 左側「+ 新對話」
3. **切換歷史** — 左側列表，按時間分群（昨天 / 過去 7 天）

## 引用來源（citation）

當 AI 用了知識庫，會在訊息下方顯示**引用 chip**：

```
[1 採購流程.pdf 87%]  [2 SOP-2024.docx 75%]  [3 ...]
```

- **hover** → 顯示深色 popover，預覽該段文字
- **click** → 開右側 ArtifactPane 看完整內容 + 複製 + ESC 關

## 展開長訊息

助理回應 ≥ 600 字 或 含 code block / 表格 / heading 時，hover 訊息會出現「📤 展開」：
- 點開右側 ArtifactPane 整段 markdown 渲染（heading 階層、code 高亮、表格）
- 可複製整段、ESC 關

## Project scope binding

若你在 Project picker 選了一個 Project：
- 歡迎畫面會顯示「{emoji} 使用 Project：{name} · N 個 KB 自動加入 RAG」
- 新對話自動把 Project 的 KB list 帶進 RAG context
- 對話 title 自動加 `[{emoji} {name}]` prefix

切離 Project → 之後新對話又回空 KB。

## 鍵盤快捷

| 鍵 | 功能 |
|---|---|
| Enter | 送出 |
| Shift+Enter | 換行 |
| ⌘K / Ctrl+K | 開 command palette（全域搜尋功能） |
| Esc | 關 ArtifactPane |

---

下一篇：[03-knowledge-base.md](./03-knowledge-base.md)
