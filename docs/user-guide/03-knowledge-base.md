# 知識庫（KB）

## 建第一個 KB

1. 進「知識庫」分頁 → 「建立知識庫」
2. 填名稱（例：「採購規範」）
3. 選**建立模式**：
   - 📁 **手動上傳**（預設）— 之後拖檔
   - 🌐 **從 URL 匯入** — 直接餵 URL（單個 / 多個 / sitemap.xml）
4. 選**切片策略**：
   - **auto**（預設，依內容偵測）
   - recursive 字符 / markdown / Q&A
5. chunk_size / overlap 通常用預設 512 / 64
6. 按「建立」

## 上傳文件

進 KB 詳情頁：
- **拖檔**到頁面任何位置（含 PDF / Word / Markdown / Excel）
- 或點「上傳檔案」選
- 進度條會顯示「pending → processing → ready」（小檔 30 秒、PDF 30 頁 ~2 分鐘）

## 文件操作

每份文件可：
- 看 chunks（點檔名展開段落）
- 重切（改 chunk_strategy / size）
- 啟用 / 停用（停用 = 不參與 RAG 但保留）
- 命中策略 chip：`rag`（向量檢索）/ `direct`（整段塞 context）
- Q&A 生成（按鈕「生成問答對」自動讓 LLM 抽 Q&A）
- 刪除

## Web 同步（從 URL）

見 [06-web-sync.md](./06-web-sync.md)。

## 命中測試

KB 卡片 →「檢索測試」：
- 輸入 query
- 看命中段落 + 分數
- 用來 debug RAG 為何抓對 / 抓錯

## 資料夾 / Tags / ACL

- **資料夾** — 左側樹，可拖 KB 到資料夾
- **Tags** — 文件層級，多選 chip filter
- **ACL** — KB 卡片 hover 出「資源授權」icon，per-KB 設特定 user / role 可看

## 加入 Project

KB 卡片 hover 出「+ 加入專案」icon，選 Project → 該 Project active 時 chat 會自動帶這個 KB。

---

下一篇：[04-create-app.md](./04-create-app.md)
