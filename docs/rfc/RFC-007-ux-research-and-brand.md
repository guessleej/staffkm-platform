# RFC-007：UX 研究交付 + 品牌升級藍圖

| 欄位 | 內容 |
|---|---|
| 編號 | RFC-007 |
| 提案者 | @leeweiye |
| 狀態 | Draft |
| 建立日期 | 2026-05-16 |
| 取代 / 被取代 | 無 |

---

## 1. 摘要
M1 收尾的兩個非工程性交付物：UX 研究結論 + 品牌升級方向。本 RFC 把目標、限制、評估方式定下來，實際視覺資產（logo / icon / 配色微調）由設計協作者完成後逐 PR 落地。

## 2. UX 研究現況觀察（自我評估）

實際操作累積的 UX 發現：

| 觀察 | 影響 |
|---|---|
| 使用者無法分辨「stub 頁面」與「當機」 | 已由 PR #65（UnderConstructionView）改善 |
| 對話為中心後管理頁面像「次要功能」 | 符合 claude.ai 風格但需引導 |
| Workspace 切換器埋在右上角，新使用者不易發現 | 待補：登入後 onboarding |
| 多個列表 page 都各自實作搜尋／批量 toolbar | 已收斂為共用 primitive（B-3） |
| Folder 樹只在 KB 出現，App / Tool 沒有 | 已由 D-5 統一後端，前端待接 |
| Chat 訊息流無頭像但無時間戳 | 視場景補回（後續 PR） |

## 3. UX 研究後續行動

1. **5 個使用者一週日記**：邀請真實使用者試用 1 週，每日記錄 1 個痛點
2. **任務型測試（5 個典型場景）**：
   - 建立第一個 KB 並上傳文件
   - 用 Application 模板問答
   - 用 Project 打包 KB + App
   - 試跑 Tool（HTTP）
   - 回滾 Application 設定
3. **熱點圖 + Session replay**：M2 期間加入 PostHog 或自架 OSS
4. **每月 NPS / SUS 量表**：4-6 題 Google Form

## 4. 品牌升級方向

### 4.1 不動的元素
- Logo wordmark：「staffKM」字樣（已是品牌資產）
- 品牌主色：brand-600 indigo（已寫進 design tokens）
- 「對話為中心」UX 哲學（RFC-006）

### 4.2 需要設計協作的元素
| 項目 | 現況 | 升級方向 |
|---|---|---|
| App icon | "S" 漸層方塊 | 自訂 logo mark（需設計師） |
| Favicon | 預設 | 配合 logo |
| Empty state 插畫 | 純文字 | 4-6 張線條風格插畫 |
| Loading 動畫 | 旋轉 spinner | 客製 brand 動畫 |
| Marketing 首頁 | 無 | 落地頁設計 |
| 配色微調 | 已扁平化（PR #55） | 加 brand accent 色 |

### 4.3 待決策
1. 是否做 light / dark 兩套 logo？（建議：是）
2. 字體要不要換？（建議：先用系統字 + 後續評估 Noto Sans TC + Inter）
3. Marketing site 用什麼技術棧？（建議：Astro + 沿用 design-tokens）

## 5. 評估指標（給 M1 GA 用）

| 指標 | 現況 | 目標 |
|---|---|---|
| 「點功能進去都空白」回報 | 已修 3 次 | 0 |
| 新使用者建第一個 KB 需要的步驟數 | 未測 | ≤ 5 步 |
| 平均對話建立時間 | 未測 | ≤ 30 秒 |
| Project / Folder 雙重組織心智成本 | 未測 | A/B 後決定 |

## 6. 不在本 RFC 範圍
- 實際 Logo / icon 視覺資產（待設計協作）
- 實際 marketing site 內容
- 多語系翻譯細節（i18n 框架由 C-4 處理）

## 7. 後續行動
- M1 GA 前：完成 UnderConstructionView 推廣到所有 stub page ✓（PR #65）
- M2 起：每個新 backlog 條目都附 5-10 字的「對使用者價值」描述
- 與設計師敲定 logo / 插畫風格的 spec sheet（另案）
