import { http } from './index'

export const authApi = {
  async login(username: string, password: string) {
    const { data } = await http.post('/auth/login', { username, password })
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
