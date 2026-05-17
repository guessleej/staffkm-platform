import { createI18n } from 'vue-i18n'

import zhTW from './locales/zh-TW'
import zhCN from './locales/zh-CN'
import en   from './locales/en'

export type Locale = 'zh-TW' | 'zh-CN' | 'en'

const STORAGE_KEY = 'staffkm.locale'
const DEFAULT_LOCALE: Locale = 'zh-TW'

function pickInitialLocale(): Locale {
  const saved = localStorage.getItem(STORAGE_KEY) as Locale | null
  if (saved === 'zh-TW' || saved === 'zh-CN' || saved === 'en') return saved
  // 從 navigator 偵測：zh-cn/zh-hans 走簡中、其他 zh 走繁中、其餘英文
  const nav = (navigator.language || DEFAULT_LOCALE).toLowerCase()
  if (nav.startsWith('zh-cn') || nav.startsWith('zh-hans') || nav.startsWith('zh-sg')) return 'zh-CN'
  if (nav.startsWith('zh')) return 'zh-TW'
  return 'en'
}

export const i18n = createI18n({
  legacy: false,                    // Composition API 模式
  locale: pickInitialLocale(),
  fallbackLocale: DEFAULT_LOCALE,
  globalInjection: true,            // 模板內可直接用 $t
  messages: {
    'zh-TW': zhTW,
    'zh-CN': zhCN,
    en,
  },
})

/** 切換語系並落地 localStorage。 */
export function setLocale(locale: Locale) {
  i18n.global.locale.value = locale
  localStorage.setItem(STORAGE_KEY, locale)
  document.documentElement.lang = locale
}

export const SUPPORTED_LOCALES: { code: Locale; label: string }[] = [
  { code: 'zh-TW', label: '繁體中文' },
  { code: 'zh-CN', label: '简体中文' },
  { code: 'en',    label: 'English' },
]
