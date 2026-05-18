import { AxiosInstance } from 'axios'

export class ApplicationsResource {
  constructor(private http: AxiosInstance) {}

  async list(): Promise<any[]> {
    const r = await this.http.get('/api/v1/applications')
    return r.data?.data ?? []
  }

  async create(name: string, type = 'chat', extra: Record<string, any> = {}): Promise<any> {
    const r = await this.http.post('/api/v1/applications', { name, type, ...extra })
    return r.data?.data ?? r.data
  }

  async get(id: string): Promise<any> {
    const r = await this.http.get(`/api/v1/applications/${id}`)
    return r.data?.data ?? r.data
  }

  async run(id: string, inputs: Record<string, any>): Promise<any> {
    const r = await this.http.post(`/api/v1/applications/${id}/run`, { inputs })
    return r.data
  }
}
