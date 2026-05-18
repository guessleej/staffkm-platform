import { AxiosInstance } from 'axios'

export class WorkspacesResource {
  constructor(private http: AxiosInstance) {}

  async list(): Promise<any[]> {
    const r = await this.http.get('/api/v1/workspaces')
    return r.data?.data ?? []
  }

  async create(name: string, slug?: string): Promise<any> {
    const r = await this.http.post('/api/v1/workspaces', { name, slug })
    return r.data?.data ?? r.data
  }

  async get(id: string): Promise<any> {
    const r = await this.http.get(`/api/v1/workspaces/${id}`)
    return r.data?.data ?? r.data
  }
}
