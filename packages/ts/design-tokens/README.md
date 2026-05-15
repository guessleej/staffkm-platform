# @staffkm/design-tokens

> 設計系統的單一真相來源（single source of truth）。所有顏色 / 間距 / 字型 / 陰影 / 動效在此定義為 CSS variables，並產生 Tailwind preset 與 TS 型別。

## 為什麼這樣設計

1. **CSS variables 而非寫死數值** → 主題切換（light/dark/品牌色）只改變數，不重 build
2. **HSL 三元組（不是 hex）** → `hsl(var(--color-brand-500) / 0.2)` 可動態套透明度
3. **Tailwind preset** → 既有 `bg-brand-600`、`text-success-700` 用法不變
4. **TS 型別** → IDE 自動完成 token 名稱

## 包含

```
tokens/
├── colors.css           # 6 個 role × 4-11 階 = 80+ color tokens
├── spacing-radius.css   # spacing / radius / shadow / z-index / motion
├── typography.css       # font family / size / weight / line height
└── index.css            # 匯總入口（含 base styles）

src/index.ts             # TS 常數 + helper 函式
tailwind.preset.cjs      # Tailwind preset
```

## 用法

### CSS

```css
/* main.css */
@import "@staffkm/design-tokens/css";

.my-component {
  background: hsl(var(--color-surface-raised));
  color: hsl(var(--color-text-primary));
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  transition: all var(--duration-base) var(--ease-out);
}
```

### Tailwind

```js
// tailwind.config.js
import preset from '@staffkm/design-tokens/tailwind'
export default {
  presets: [preset],
  content: ['./src/**/*.{vue,ts}'],
}
```

```vue
<button class="bg-brand-600 hover:bg-brand-700 text-white shadow-md rounded-lg">
  點我
</button>
```

### TypeScript

```ts
import { colors, intents, token, tokenAlpha } from '@staffkm/design-tokens'

const primary = token('brand-600')              // → 'hsl(var(--color-brand-600))'
const subtle  = tokenAlpha('brand-500', 0.2)    // → 'hsl(var(--color-brand-500) / 0.2)'
```

## Color tokens（80+）

```
brand     50 100 200 300 400 500 600 700 800 900 950   ← 主品牌色
neutral   50 100 200 300 400 500 600 700 800 900 950   ← warm gray
success    50              500 600 700                  ← 綠色
warning    50              500 600 700                  ← 橘色
danger     50              500 600 700                  ← 紅色
info       50              500 600 700                  ← 藍色

surface   base / raised / overlay / sunken              ← 背景階層
text      primary / secondary / tertiary / on-brand    ← 文字色
border    subtle / default / strong / focus            ← 邊框色
```

## Dark mode

加 `dark` class 或 `[data-theme="dark"]` 屬性到 `<html>`，所有 surface / text / border 變數自動翻轉：

```html
<html class="dark">
```

## 換主題（一行）

把 `colors.css` 的 `--color-brand-*` 11 行換成你的品牌色就完成。

## 路線圖

- v0.1（本版本）：基礎 token + Tailwind preset
- v0.2：style dictionary 整合（產生 iOS / Android / Figma token）
- v0.3：主題編輯器 UI（管理員可在 admin 設定品牌色）
