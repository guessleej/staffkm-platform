import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../api/auth'

interface UserInfo {
  id: string
  username: string
  display_name: string | null
  email: string | null
  roles: string[]
  department: string | null
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserInfo | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))

  // 只看 token；user 由 init() 非同步補齊（避免 reload 時的 race condition）
  const isAuthenticated = computed(() => !!accessToken.value)

  function hasRole(roles: string[]): boolean {
    return roles.some(r => user.value?.roles.includes(r))
  }

  // 同一個 init() 進行中的 promise，避免多個 caller（App.vue + router.beforeEach + 元件 mount）
  // 在 token 已存在但 user 還沒回填時各自打 /auth/me 6 次。
  let _initPromise: Promise<void> | null = null

  async function init() {
    if (!accessToken.value || user.value) return
    if (_initPromise) return _initPromise
    _initPromise = (async () => {
      try {
        const me = await authApi.getMe()
        user.value = me
      } catch {
        logout()
      } finally {
        _initPromise = null
      }
    })()
    return _initPromise
  }

  async function login(username: string, password: string, captcha?: { token: string; answer: string }) {
    const data = await authApi.login(username, password, captcha)
    accessToken.value = data.access_token
    user.value = data.user
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
  }

  function logout() {
    user.value = null
    accessToken.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  return { user, accessToken, isAuthenticated, hasRole, init, login, logout }
})
