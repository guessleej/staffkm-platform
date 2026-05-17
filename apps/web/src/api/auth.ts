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
}
