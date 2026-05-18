import { http } from './index'

export interface Captcha { token: string; question: string }

export const authApi = {
  async login(username: string, password: string, captcha?: { token: string; answer: string }) {
    const body: Record<string, unknown> = { username, password }
    if (captcha) {
      body.captcha_token  = captcha.token
      body.captcha_answer = captcha.answer
    }
    const { data } = await http.post('/auth/login', body)
    return data.data
  },
  async getCaptcha(): Promise<Captcha> {
    const { data } = await http.get('/auth/captcha')
    return data.data
  },
  async getMe() {
    const { data } = await http.get('/auth/me')
    return data.data
  },
  async logout() {
    await http.post('/auth/logout')
  },
  async oidcInfo(): Promise<{ enabled: boolean; display_name: string }> {
    try {
      const { data } = await http.get('/auth/oidc/info')
      return data.data
    } catch {
      return { enabled: false, display_name: 'SSO' }
    }
  },
  oidcLoginUrl(next: string = '/'): string {
    const base = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')
    return `${base}/auth/oidc/login?next=${encodeURIComponent(next)}`
  },
  // v4.1 A: public 14-day trial signup
  async trialSignup(body: { email: string; password: string; workspace_name: string }) {
    const { data } = await http.post('/auth/trial', body)
    return data.data as {
      workspace_id: string
      user_id: string
      trial_expires_at: string
      next_step: string
    }
  },

  // ── v4.6 F: account self-service ──────────────────────────────
  async sendVerifyEmail(email: string) {
    const { data } = await http.post('/auth/verify-email/send', { email })
    return data
  },
  async confirmVerifyEmail(token: string) {
    const { data } = await http.post('/auth/verify-email/confirm', { token })
    return data.data as { email: string }
  },
  async forgotPassword(email: string) {
    const { data } = await http.post('/auth/forgot-password', { email })
    return data
  },
  async resetPassword(token: string, newPassword: string) {
    const { data } = await http.post('/auth/reset-password', {
      token,
      new_password: newPassword,
    })
    return data
  },

  // ── v4.6 F: self-service OAuth (Google / GitHub) ──────────────
  async oauthAuthorize(provider: 'google' | 'github') {
    const requestUrl = window.location.origin
    const { data } = await http.get(
      `/auth/oauth/${provider}/authorize`,
      { params: { request_url: requestUrl } },
    )
    return data.data as { authorize_url: string; state: string; redirect_uri: string }
  },
}
