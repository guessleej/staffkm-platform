import { AxiosInstance } from 'axios'

export class PluginsResource {
  constructor(private http: AxiosInstance) {}

  async list(): Promise<any[]> {
    const r = await this.http.get('/api/v1/plugins')
    return r.data?.data ?? []
  }

  async reload(): Promise<any> {
    const r = await this.http.post('/api/v1/plugins/reload')
    return r.data
  }
}
