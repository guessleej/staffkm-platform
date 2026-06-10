import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'

import { useWorkspaceStore } from '@/stores/workspace'

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 60_000,
})

http.interceptors.request.use(async (config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`

  // v3.1：自動帶 workspace header → gateway proxy 會據此把 path 注成
  // /api/v1/workspace/{ws}/... 直接命中 workspace-scoped router，
  // 不再走 LegacyURLBridge（v3.1 起預設 410）。
  // try/catch 包是因為 login 前 Pinia 未 init 會炸。
  try {
    const store = useWorkspaceStore()
    // v5.13 race 修：currentId 來自 localStorage（每個來源獨立）。剛登入 / 換到新來源
    // （如 http→https）時 localStorage 空 → currentId 還沒就緒，子層 onMounted 的
    // workspace-scoped 請求（如 /agents）會搶在 workspace.load() 之前送 → 缺
    // X-Workspace-ID → gateway 退 legacy → 後端 404。故：除 auth/workspaces/public
    // 外，currentId 未就緒就先 await ensureReady()（/workspaces 本身不能 await，否則 deadlock）。
    const path = config.url || ''
    const skipWs = /^\/?(auth|workspaces|public)(\/|$)/.test(path)
    if (token && !skipWs && !store.currentId) {
      await store.ensureReady()
    }
    const ws = store.currentId
    if (ws) {
      config.headers = config.headers || {}
      config.headers['X-Workspace-ID'] = ws
    }
  } catch {
    // Pinia 未 init（login 前 / app bootstrap 早期）→ 略過
  }

  return config
})

// — 401 處理（強化版）—
// 1) 多個 concurrent 401 共用同一個 refresh promise（避免 N 次 /auth/refresh）
// 2) refresh 端點本身 401 → 直接登出，不要遞迴
// 3) 同一個 request 已 retry 過 → 不再 retry
// 4) refresh 失敗 → 清 token + 跳 /login?next=（除非已在 /login）
let _refreshing: Promise<string> | null = null
function _doRefresh(): Promise<string> {
  if (_refreshing) return _refreshing
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) return Promise.reject(new Error('no refresh token'))
  _refreshing = axios
    .post('/api/v1/auth/refresh', { refresh_token: refreshToken })
    .then(({ data }) => {
      const t = data?.data?.access_token
      if (!t) throw new Error('refresh response missing access_token')
      localStorage.setItem('access_token', t)
      return t
    })
    .finally(() => { _refreshing = null })
  return _refreshing
}

function _goLogin() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  if (!location.pathname.startsWith('/login')) {
    // 帶 next 參數，登入後可導回原頁
    const next = encodeURIComponent(location.pathname + location.search)
    location.href = `/login?next=${next}`
  }
}

http.interceptors.response.use(
  (res) => res,
  async (err: AxiosError) => {
    const cfg = err.config as InternalAxiosRequestConfig & { _retried?: boolean } | undefined
    const status = err.response?.status

    // refresh 端點本身 401 → 直接登出，不要遞迴
    if (status === 401 && cfg?.url?.includes('/auth/refresh')) {
      _goLogin()
      return Promise.reject(err)
    }

    // 一般 401 + 還沒 retry 過 → 試 refresh 一次
    if (status === 401 && cfg && !cfg._retried) {
      try {
        const newToken = await _doRefresh()
        cfg._retried = true
        cfg.headers.Authorization = `Bearer ${newToken}`
        return http(cfg)
      } catch {
        _goLogin()
        return Promise.reject(err)
      }
    }

    return Promise.reject(err)
  }
)
