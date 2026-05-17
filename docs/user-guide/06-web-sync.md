# Web 同步 — 從 URL / sitemap 建 KB

## 3 種模式

| 模式 | 適用 |
|---|---|
| **單一 URL** | 一篇文章 / 一個說明頁 |
| **多 URL 清單** | 你心裡已知的 N 個頁面，最多 20 |
| **sitemap.xml** | 整個 docs 站，自動解析、可 filter |

## 操作

`/knowledge` → 「建立知識庫」 → 切「🌐 從 URL 匯入」

### 單 URL / 多 URL

切「📝 URL 清單」子模式：
- textarea 一行一個 URL（最多 20）
- 即時顯示「準備同步 N 個」
- 按鈕變「建立並抓取 N 個 URL」

每個 URL 變成一份獨立 inline doc，後台用 trafilatura 抽文（JS-only 頁面可能抽不到）。

### sitemap.xml

切「🗺️ sitemap.xml」子模式：
- sitemap URL（例：`https://www.python.org/sitemap.xml`）
- 最大 URL 數（1-100）
- URL 子字串 filter（選填，例：`/docs/` 只取文件頁不取首頁）

支援 sitemap-index（recursive 一層，最多 5 個 sub-sitemap，每個拆 N 個 URL）。

按「建立並解析 sitemap」→ alert 顯示「找到 X 個 URL，已排程同步」。

## 同步狀態

KB 卡片右下角會顯示來源 chip：
- 🌐 `https://docs.example.com/handbook` — Web 來源 + URL
- ⚡ Workflow 寫入

同步中會看到「同步中」/「失敗」labels。

## 重新同步（upsert）

對同 KB 同 URL 再 sync 一次，**會自動覆蓋舊版**（用 `upsert_key=web:{url}`），不會建多份。

## 限制

- 單個 URL 最大 30 秒 timeout
- HTML 抽文用 trafilatura — JS-rendered SPA 抽不到
- 多 URL / sitemap 各任務 countdown 錯開避免打爆對方
- 沒有 robots.txt / rate-limit 偵測（v3 候選）

---

下一篇：[07-embed-widget.md](./07-embed-widget.md)
