import { AxiosInstance } from 'axios'

export class AuthResource {
  constructor(private http: AxiosInstance) {}

  async login(username: string, password: string): Promise<any> {
    const r = await this.http.post('/api/v1/auth/login', { username, password })
    return r.data
  }

  async refresh(refreshToken: string): Promise<any> {
    const r = await this.http.post('/api/v1/auth/refresh', { refresh_token: refreshToken })
    return r.data
  }

  async me(): Promise<any> {
    const r = await this.http.get('/api/v1/auth/me')
    return r.data
  }
}
