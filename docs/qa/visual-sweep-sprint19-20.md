# Visual Sweep — Sprint 19-20 新 UI / 新流程

> 自動 DOM audit 結論：5 個 UI + 3 個流程 **零硬性 bug**
> （無 inline hex 色碼、無 unlabeled inputs、empty state 都在、active nav 都對）。
>
> 視覺細節仍需人眼跑一輪。下面是建議 walkthrough。

## 5 個新 UI

| 路徑 | 應驗證 | 自動 audit |
|------|--------|----------|
| `/mcp/servers` | empty CTA → 新增 server modal → 三種 transport chip → tools drawer | ✅ h1 / 6 buttons / empty state |
| `/triggers` | empty CTA → 新增（先建 App）→ 3 種 kind toggle → runs drawer | ✅ h1 / 6 buttons / empty state |
| `/memories` | scope chip filter → 新增 modal → importance slider → search input | ✅ h1 / 10 buttons / empty state |
| `/admin/usage` | StatCard × 3 (token/cost/req) → SProgress bar → quota form 設值 | ✅ h1 / 5 cards |
| `/applications/X/workflow` 節點版本 | 「節點版本」按鈕 → drawer → 快照 + 列表 + 回滾 | ⏳ 無 workflow app 可測 |

## 3 個新流程

### A. **Sitemap crawler**（PR #159）
1. `/knowledge` → 「建立知識庫」
2. 切「🌐 從 URL 匯入」tab → 切「🗺️ sitemap.xml」子模式
3. 填名稱 + sitemap.xml URL（例 `https://www.python.org/sitemap.xml`）
4. 設 max_urls=5, filter=`/docs/`（可選）
5. 按「建立並解析 sitemap」
6. **應收 alert「從 sitemap 找到 N 個 URL，已排程同步」**
7. 進該 KB 詳情，應看到 N 個 inline doc 陸續變 ready

### B. **Workspace 自訂模板**（PR #157）
1. `/applications` → 任一 App 卡片 hover → 「存模板」按鈕
2. 開 dialog → 改名 + emoji → 儲存
3. 點頂「✨ 從模板建立」→ 應看到分類 chip 多出「✨ 我的模板 (N)」
4. 切該 chip → 卡片右上有「自訂」chip + warning border + 底部有 🗑 刪除
5. 點「使用此模板」→ form prefill 正確

### C. **Project chat scope binding**（PR #158）
1. `/projects` → 建一個 Project，加 1-2 個 KB
2. 切到該 Project（picker 或 /projects 卡片「切換到此」）
3. 進 `/chat` → 歡迎畫面應顯示 brand chip：
   「{emoji} 使用 Project：{name} · N 個 KB 自動加入 RAG」
4. 發訊息 → 新對話 title 應含「[# Project name]」
5. 訊息回應應該帶 KB citations

## 已知非 bug

| 現象 | 為何 |
|---|---|
| LoginView 左側深藍 panel 不切 dark | intentional brand design |
| `bg-brand-50` / `bg-warning-50` accent 永遠淺 | semantic 色，全主題一致 |
| 截圖 timeout 偶發 | Chrome MCP CDP 偏好較長 sleep；不影響功能 |

## 抓到 bug 怎麼回報

- 截圖
- 路徑 + 操作步驟
- 預期行為
- 加 `theme:dark` label 如果是 dark mode 相關
