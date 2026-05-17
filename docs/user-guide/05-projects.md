# Project — 把相關的東西綁一起

## 為什麼有 Project

當你有多種業務領域（人事 / 採購 / 客服），每次 chat 都要手選 KB 很麻煩。Project 解這個：
- 把相關的 KB + App 綁進一個 Project
- 切到該 Project 後，chat 自動帶這些 KB 進 RAG

## 建 Project

1. 頂 nav 右側 picker 「# 尚無資料」→ 「建立 Project」（或 `/projects` → 「建立」）
2. 填：
   - emoji（看起來好辨識）
   - 名稱（例：「人事 SOP 諮詢」）
   - 說明（選填）
   - System Prompt（選填，所有 chat 都會帶這段 prompt prefix）

## 加入資源

| 資源 | 怎麼加 |
|---|---|
| KB | `/knowledge` 卡片 hover → 「+」icon → 勾 Project |
| App | `/applications` 卡片 hover → 「+」icon → 勾 Project |

也可以從 `/projects` 詳情頁批次選。

## 切到 Project

頂 nav picker 選一個 → chat 歡迎畫面會出現 brand chip：

```
🏢 使用 Project：人事 SOP 諮詢 · 3 個 KB 自動加入 RAG
```

新對話自動帶這 3 個 KB，title 變 `[🏢 人事 SOP 諮詢] 新對話`。

## 離開 Project

picker → 「離開目前 Project」 → 之後 chat 又空 KB。

既有對話的 KB scope **不變**（freeze 在 create 當下）。

## 管理 Project

`/projects` 頁列出所有 Project：
- 看包含的 KB / App 數
- 切換 / 編輯 / 刪除
- 「使用中」chip 標目前 active

刪 Project **不會刪 KB / App**，只解除關聯。

## Tips

- 建議 Project 數量 3-10 個（每個業務領域一個）
- 跨 Project 共用的 KB（例：「通用詞彙表」）可加進多個 Project
- 一個 Project 可以含多個 LLM 應用，使用者自選

---

下一篇：[06-web-sync.md](./06-web-sync.md)
