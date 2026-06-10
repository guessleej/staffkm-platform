import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { i18n } from './i18n'

// 設計 tokens 必須在 Tailwind 之前，CSS variables 才能被 utility class 引用
import '@staffkm/design-tokens/css'
import './styles/index.css'

// v5.12: Vite 在「動態 import 的 module 載入失敗」時於 window 派發 vite:preloadError
//   （新部署換 chunk hash → 舊分頁的 lazy component/route 載不到 → 白屏卡死）。偵測到就整頁重載
//   抓新 bundle。router.onError 只接「導航觸發」的；非導航的 lazy component（如對話框）走這條。
//   防迴圈：同一 session 只自動重載一次。
window.addEventListener('vite:preloadError', () => {
  if (sessionStorage.getItem('staffkm.preload_reload')) return
  sessionStorage.setItem('staffkm.preload_reload', '1')
  window.location.reload()
})

import AdminHelp from './components/common/AdminHelp.vue'

const app = createApp(App)
app.component('AdminHelp', AdminHelp)   // 全域：admin 頁說明卡，各頁免 import
app.use(createPinia())
app.use(router)
app.use(i18n)
app.mount('#app')
