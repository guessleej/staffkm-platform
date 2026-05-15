// Tailwind config — 接通 @staffkm/design-tokens preset，所有顏色 / 圓角 / 陰影 / 字型走 CSS variables
import preset from '@staffkm/design-tokens/tailwind'

/** @type {import('tailwindcss').Config} */
export default {
  presets: [preset],
  content: [
    './index.html',
    './src/**/*.{vue,ts,tsx}',
    // 也掃描 ui-kit 元件中的 class，避免 PurgeCSS 砍掉
    '../../packages/ts/ui-kit/src/**/*.{vue,ts}',
  ],
  // preset 已涵蓋 fontFamily / colors / radius / shadow，不在這裡 extend 以保持單一真相來源
}
