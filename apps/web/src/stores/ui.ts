/** 全域 UI 偏好 — 側欄折疊、深色模式、語系等。 */
import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

const KEY_COLLAPSED = 'staffkm.sidebar_collapsed'
const KEY_THEME     = 'staffkm.theme'

type Theme = 'light' | 'dark' | 'system'

function applyTheme(t: Theme) {
  const root = document.documentElement
  if (t === 'system') {
    const dark = window.matchMedia('(prefers-color-scheme: dark)').matches
    root.classList.toggle('dark', dark)
  } else {
    root.classList.toggle('dark', t === 'dark')
  }
}

export const useUIStore = defineStore('ui', () => {
  const sidebarCollapsed = ref(localStorage.getItem(KEY_COLLAPSED) === '1')
  const theme = ref<Theme>((localStorage.getItem(KEY_THEME) as Theme) || 'light')

  // 套用初始 theme
  applyTheme(theme.value)

  // theme 變動 → DOM + localStorage
  watch(theme, (v) => {
    localStorage.setItem(KEY_THEME, v)
    applyTheme(v)
  })

  // sidebar 變動 → localStorage
  watch(sidebarCollapsed, (v) => {
    localStorage.setItem(KEY_COLLAPSED, v ? '1' : '0')
  })

  // 跟隨系統 dark 變化（只在 theme=system 時）
  if (window.matchMedia) {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    mq.addEventListener('change', () => {
      if (theme.value === 'system') applyTheme('system')
    })
  }

  function toggleSidebar() { sidebarCollapsed.value = !sidebarCollapsed.value }
  function toggleTheme()   { theme.value = theme.value === 'dark' ? 'light' : 'dark' }

  const isDark = computed(() => {
    if (theme.value === 'system') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches
    }
    return theme.value === 'dark'
  })

  return { sidebarCollapsed, theme, isDark, toggleSidebar, toggleTheme }
})
