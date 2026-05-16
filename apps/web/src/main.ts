import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { i18n } from './i18n'

// 設計 tokens 必須在 Tailwind 之前，CSS variables 才能被 utility class 引用
import '@staffkm/design-tokens/css'
import './styles/index.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(i18n)
app.mount('#app')
