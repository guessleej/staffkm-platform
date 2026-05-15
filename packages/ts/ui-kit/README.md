# @staffkm/ui-kit

> staffKM Vue 3 元件庫。所有元件以 `S` 前綴命名（避開 HTML 與其他庫衝突），使用 `@staffkm/design-tokens` 作為視覺基礎。

## 已包含元件（v0.1.0）

| 元件 | 用途 |
|------|------|
| `SAlert`    | 訊息提示橫幅（info / success / warning / danger）|
| `SAvatar`   | 使用者頭像（圖片 / 縮寫 / 漸層回退）|
| `SBadge`    | 小型狀態標籤（subtle / solid / outline）|
| `SButton`   | 按鈕（primary / secondary / ghost / danger / link）|
| `SCard`     | 卡片容器（含 header / body / footer slot）|
| `SEmpty`    | 空狀態（含圖示 / 標題 / 描述 / 動作 slot）|
| `SInput`    | 文字輸入（含 label / hint / error / icon slot）|
| `SModal`    | 對話框（teleport + ESC + backdrop click 關閉）|
| `SSpinner`  | 載入指示器 |
| `STag`      | 標籤（可關閉、6 種 intent）|
| `STextarea` | 多行輸入（含字數計數）|

## 安裝

```bash
pnpm add @staffkm/ui-kit @staffkm/design-tokens
```

## 用法

### 1. 在你的 entry CSS 引入 design tokens

```css
/* main.css */
@import "@staffkm/design-tokens/css";
@import "tailwindcss/preflight";
@import "tailwindcss/utilities";
```

### 2. Tailwind 設定使用 preset

```js
// tailwind.config.js
import preset from '@staffkm/design-tokens/tailwind'
export default {
  presets: [preset],
  content: [
    './src/**/*.{vue,ts,tsx}',
    './node_modules/@staffkm/ui-kit/src/**/*.vue',
  ],
}
```

### 3. 在元件中使用

```vue
<script setup lang="ts">
import { SButton, SCard, SEmpty } from '@staffkm/ui-kit'
import { ref } from 'vue'
const open = ref(false)
</script>

<template>
  <SCard title="文件管理" subtitle="共 0 筆">
    <SEmpty title="尚無文件" description="點擊右上角按鈕上傳第一個檔案">
      <template #action>
        <SButton variant="primary">上傳文件</SButton>
      </template>
    </SEmpty>
  </SCard>
</template>
```

## Storybook（互動文件）

```bash
cd packages/ts/ui-kit
pnpm install
pnpm storybook
# → http://localhost:6006
```

## 設計原則

1. **無狀態**：所有元件用 props 控制；複雜狀態（如 form validation）由呼叫端管理
2. **a11y first**：focus-visible、aria 標籤、鍵盤導航內建
3. **不假設外部依賴**：除了 design tokens 與 Vue 3 核心，不依賴其他 UI 庫
4. **TypeScript 型別完整**：所有 props / emits 有型別

## 路線圖

- v0.1（本版本）：11 個基礎元件
- v0.2：表單元件（Select / Checkbox / Radio / Switch / DatePicker）
- v0.3：資料展示（Table / Pagination / Tabs / Stepper）
- v0.4：導航（Breadcrumb / Menu / Sidebar / Drawer）
- v0.5：複合元件（Toast 系統 / Tooltip / Popover / Command Palette）
