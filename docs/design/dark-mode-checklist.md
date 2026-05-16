# Dark Mode 全量化清單 v1

> 設計系統 v1.1 同 PR 的伴隨文件。
> **目標**：讓 staffKM 的 dark mode 真的可用，而不是「能切但很多元件變色」。

## 1. 現況

- `colors.css` 已定義完整 dark scheme（`:root.dark` 區塊）✓
- Tailwind preset 已開 `darkMode: ['class', '[data-theme="dark"]']` ✓
- 設計系統 v1.1 新增 `text-fg` / `bg-surface-*` / `border-bd-*` tokens（會自動 dark flip）

但**多數 view 仍寫死** `text-gray-700` / `bg-white` / `border-gray-200`：
- 在 dark mode 下文字仍是 90% 黑（因為 `gray-*` alias 到 `neutral-*`，而 neutral-50 在 dark 是淺色）
- 部分 `bg-white` 直接 hard-coded → dark mode 變白底破壞統一感

## 2. 必修清單（按優先序）

### Tier 1 — 全域常見元件（影響每頁）
- [ ] `DashboardLayout.vue` header / 使用者選單
- [ ] `ChatLayout.vue` 側欄
- [ ] `ToastHost.vue` / `DialogHost.vue` / `CommandPalette.vue`
- [ ] `WorkspaceSwitcher.vue`
- [ ] `EntityFolderSidebar.vue`

### Tier 2 — 主要列表頁
- [ ] `ApplicationListView.vue`
- [ ] `KnowledgeView.vue`
- [ ] `ToolListView.vue` / `SkillListView.vue` / `DataSourceListView.vue`
- [ ] `UsageView.vue`
- [ ] `ModelProviderView.vue`

### Tier 3 — 編輯 / 設定頁
- [ ] `WorkflowEditorView.vue`（含 NodeConfigPanel）
- [ ] `DocumentView.vue` / `HitTestView.vue`
- [ ] `ApplicationChatView.vue`

### Tier 4 — 不常用 / 公開
- [ ] `PublicChatView.vue`
- [ ] `UnderConstructionView.vue`
- [ ] admin/SystemView.vue

## 3. 替換規則（cheatsheet）

| Before                          | After                              | 原因                                  |
| ------------------------------- | ---------------------------------- | ------------------------------------- |
| `bg-white`                      | `bg-surface-raised`                | dark mode 變 `neutral-900`            |
| `bg-gray-50`                    | `bg-surface-sunken`                | dark 變 `0 0% 4%`                     |
| `text-gray-900`                 | `text-fg`                          | dark 變 `neutral-50`                  |
| `text-gray-700` / `text-gray-600`| `text-fg-secondary`                | dark 變 `neutral-300`                 |
| `text-gray-500` / `text-gray-400`| `text-fg-tertiary`                 | dark 變 `neutral-400`                 |
| `border-gray-200` / `border-neutral-200` | `border-bd` (或保留)        | dark 變 `neutral-700`                 |
| `border-gray-100`               | `border-bd-subtle`                 | dark 變 `neutral-800`                 |
| `hover:bg-gray-100`             | `hover:bg-surface-sunken`          | dark 也有 hover 對比                  |

> 不要全替換 `text-gray-*` → `text-fg-*`，例如 badge 內固定色（success/danger）保留。

## 4. 驗收

- [ ] 開 dark mode，主要 4 個頁面（chat/apps/knowledge/usage）外觀協調，無白色硬塊
- [ ] 文字對比 ≥ WCAG AA（用 Chrome DevTools axe 跑一遍）
- [ ] 切換 dark/light 時無「閃白」（CSS variable 即時 flip）
- [ ] 截圖前後對比，主管能在 30 秒內判斷「都好看」

## 5. 不在這次範圍

- 自動偵測系統主題（`prefers-color-scheme`）— 已實作於 `useUIStore`，這次不動
- per-user theme 偏好持久化 — 已實作（localStorage），這次不動
- 高對比模式 / a11y 模式 — 留待 M5
