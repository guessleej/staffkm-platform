# Dark mode 實機檢查清單

> 自動化 audit 結論：`bg-white` / `text-gray-*` / `text-slate-*` / `bg-gray-50/100/200`
> 殘留 = 0；DDL token 系統覆蓋 100%。
> 但是 **133 個 tailwind 語意色（indigo/rose/amber...）** 不會跟 dark mode flip，
> 它們是「永遠保持原色」的設計選擇（danger / warning / brand accent），
> 也是這份手動 checklist 主要要驗證的視覺問題。

---

## 操作

1. 進 `http://localhost/`
2. 右上角點 **🌙 月亮** 切換深色模式
3. 走過下面每個頁面，記錄問題

## 必驗頁面

### 〔Dashboard 頂 nav〕
- [ ] sun/moon 按鈕本身在兩種模式都看得清
- [ ] active 路徑高亮（brand 50 底）在 dark 應該變深 brand
- [ ] WorkspaceSwitcher / ProjectPicker dropdown 背景應跟著切

### 〔/chat〕
- [ ] 訊息背景 / 文字對比足夠
- [ ] 歷史對話 drawer 應切深底
- [ ] 助理訊息 hover 出現的「📤 展開」按鈕仍可見
- [ ] 點展開 → **ArtifactPane** 整面要切深
  - 標題列、複製按鈕、內容區
  - markdown 渲染：headings、code、quote、table
  - code block `bg-neutral-50` 在 dark 應仍可讀（github theme 不會自動切，需要的話之後切 github-dark）

### 〔/applications〕
- [ ] 卡片陰影與 border 在 dark 應仍有層次
- [ ] hover 浮起效果不變
- [ ] 「✨ 從模板建立」/「+ 空白應用」按鈕對比足
- [ ] **點 ✨ 模板** → modal：分類 chip、卡片、兩顆 CTA 都要切
- [ ] **點「🎮 立即試用」** → modal 對話流順
- [ ] AttachToProjectButton 下拉應切深

### 〔/knowledge〕
- [ ] 側邊資料夾樹背景
- [ ] KB 卡片 + 🌐 / ⚡ source badge
- [ ] 「建立知識庫」modal：tab 切換、URL textarea

### 〔/projects〕
- [ ] 卡片「使用中」chip
- [ ] 建立 / 編輯 modal 全套欄位

### 〔/applications/[id]/workflow〕（重要）
- [ ] **LogicFlow canvas 背景**（PR #146 後改為 bg-surface-sunken，dark 應為深底）
- [ ] 節點 palette 應切深
- [ ] NodeConfigPanel drawer 應切深
- [ ] 連線顏色 / 節點顏色（這些由 LogicFlow 控制，可能不會切）

### 〔/login〕（特殊）
- [ ] 左側深藍漸層保持不變（intentional design）
- [ ] 右側表單區應切深
- [ ] input focus state 仍可用
- [ ] 「登入系統」按鈕 box-shadow 不能在 dark 變太搶

---

## 已知可能視覺問題（不算 bug）

| 現象 | 為什麼 |
|------|--------|
| 刪除 / 危險動作仍是 rose 紅 | 語意色，故意全主題一致 |
| 警告仍是 amber 黃 | 同上 |
| 模板 ✨ / 試用 🎮 emoji | OS 字型，無法主題化 |
| KB 卡片 brand-50 hover | 兩種主題都看得清，不修 |

## 可能要修的問題

| 現象 | 修法（之後 sprint） |
|------|--------------------|
| highlight.js 程式碼區塊 github theme 在 dark 太亮 | 改用 `github-dark.css` 或加 prefers-color-scheme 雙載 |
| 部分 `bg-indigo-50` hover 在 dark 變太亮 | 改 `bg-brand-50` 或 `dark:bg-brand-900/30` |
| 6 行 LoginView inline gradient style | 保留（intentional） |

## 回報

請把抓到的問題列在 issue，標 `theme:dark` label，附：
- 頁面路徑
- 截圖（light + dark 對比）
- 預期行為
