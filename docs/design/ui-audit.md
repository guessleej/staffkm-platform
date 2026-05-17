# UI Audit v1（設計系統 v2 收尾用）

> 對照 v2.0 之後堆疊出的 UI 與 claude.ai / Linear / Notion 級別之差距。
> 給設計系統 v2 與後續 sprint 當清單用。

## 1. 已交付（v2 + v2.1）
- design-tokens 完整：HSL 三元組、dark mode、4 種 surface、fg/bd alias
- ui-kit 33 個元件（11 v1 + 22 v2）
- ⌘K Command Palette
- useToast / useDialog composable
- Brand guideline v1（logo + colour + typography）
- 對話為中心 layout
- Folder sidebar、批量 toolbar、抽屜 pattern

## 2. 明顯落差（必須在 sprint 13/14 處理）

### Tier S（最致命，馬上做）
- [x] **UsageView**：以 SStatCard + SProgress 重寫總覽（13-3 完成）
- [ ] **登入頁**：左側插畫 OK；右側表單缺 SInput + SButton 統一視覺
- [ ] **整體 typography 階層**：H1 / H2 / H3 / body 沒明確視覺差，看起來「平」
- [ ] **空狀態**：每個 list 頁都是純文字「尚未建立」— 需要 SEmpty 元件 + 圖示
- [ ] **資訊密度**：卡片 padding 不一致（p-3 / p-4 / p-5 / p-6 混用）

### Tier A（明顯影響第一印象）
- [ ] **KnowledgeView 卡片**：hover state 弱、無深度（缺 shadow lift）
- [ ] **ApplicationListView 卡片**：類型 badge 視覺弱
- [ ] **ModelProviderView**：dialog 內欄位 spacing 不齊、無 SSelect/SCheckbox 統一
- [ ] **WorkflowEditorView 工具列**：按鈕高度不齊（h-8 vs h-9 混用）
- [ ] **DocumentView 表格**：未套用 STable，每列 height 抖動

### Tier B（細節）
- [ ] icons 一致性：混用 inline SVG / 文字 icon
- [ ] 微動效：頁面切換、按鈕點擊缺反饋
- [ ] dark mode 全量化：tokens 在但很多 view 寫死 text-gray-* / bg-white

## 3. 不在此範圍
- 重寫整個架構（保留現有 staffKM 結構）
- 自製插畫 / 圖示庫（用文字 emoji 或 Heroicons 為主）
- 動畫庫（Framer Motion / Lottie）

## 4. 工程預估

| Sprint | 範圍 | 估計 PR |
|--------|------|---------|
| **13-3（本次）** | 用 SStatCard / SProgress 刷新 UsageView | ✅ 已合 |
| 14-1 | 登入頁 + 全域 typography token + SEmpty 升級 | 1 |
| 14-2 | KnowledgeView / ApplicationListView 卡片刷新 | 1 |
| 14-3 | ModelProviderView dialog + DocumentView 套 STable | 1 |
| 14-4 | dark mode 全量替換（Tier 1~3）| 1 |
| 14-5 | 微動效 + icon 統一 | 1 |

## 5. 驗收條件
- 主管 30 秒看不出來「這還是 v1 的 staffKM」
- 開 dark mode 任一頁不會出現白色硬塊
- 5 個 persona × 任一任務都不會卡在「找不到按鈕」
