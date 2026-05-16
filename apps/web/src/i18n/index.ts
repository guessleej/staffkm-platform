import { createI18n } from 'vue-i18n'

import zhTW from './locales/zh-TW'
import en   from './locales/en'

export type Locale = 'zh-TW' | 'en'

const STORAGE_KEY = 'staffkm.locale'
const DEFAULT_LOCALE: Locale = 'zh-TW'

function pickInitialLocale(): Locale {
  const saved = localStorage.getItem(STORAGE_KEY) as Locale | null
  if (saved === 'zh-TW' || saved === 'en') return saved
  // 從 navigator 偵測：以 zh 開頭走繁中、其他走英文
  const nav = (navigator.language || DEFAULT_LOCALE).toLowerCase()
  return nav.startsWith('zh') ? 'zh-TW' : 'en'
}

export const i18n = createI18n({
  legacy: false,                    // Composition API 模式
  locale: pickInitialLocale(),
  fallbackLocale: DEFAULT_LOCALE,
  globalInjection: true,            // 模板內可直接用 $t
  messages: {
    'zh-TW': zhTW,
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
  { code: 'en',    label: 'English' },
]
