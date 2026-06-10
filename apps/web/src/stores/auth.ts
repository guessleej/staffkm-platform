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
  must_change_password?: boolean
  last_workspace_id?: string | null
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserInfo | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))

  // 只看 token；user 由 init() 非同步補齊（避免 reload 時的 race condition）
  const isAuthenticated = computed(() => !!accessToken.value)

  // v5.12：首登強制改密旗標（出廠預設 admin = true）
  const mustChangePassword = computed(() => !!user.value?.must_change_password)

  function clearMustChangePassword() {
    if (user.value) user.value = { ...user.value, must_change_password: false }
  }

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

  // v4.6 F: 給 OAuth callback 等「非帳密 login 流程」用。
  async function setTokens(access: string, refresh: string, u: UserInfo) {
    accessToken.value = access
    user.value = u
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }

  function logout() {
    user.value = null
    accessToken.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    // v5.12: 一併清 user-scoped 持久狀態，避免同機換帳號殘留（前一人的 active project / workspace /
    //   onboarding 帶到下一人 → 列表被舊 project 篩、停在別人 workspace）。配合登出整頁重載清 pinia。
    localStorage.removeItem('staffkm.active_project_id')
    localStorage.removeItem('staffkm.current_workspace_id')
    localStorage.removeItem('staffkm.onboarding.done')
  }

  return { user, accessToken, isAuthenticated, mustChangePassword, clearMustChangePassword, hasRole, init, login, setTokens, logout }
})
