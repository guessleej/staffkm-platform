import { AxiosInstance } from 'axios'

export class QuotaResource {
  constructor(private http: AxiosInstance) {}

  async summary(): Promise<any> {
    const r = await this.http.get('/api/v1/quota/summary')
    return r.data?.data ?? r.data
  }

  async set(opts: { monthlyTokenCap?: number; monthlyCostCapUsd?: number }): Promise<any> {
    const r = await this.http.put('/api/v1/quota', {
      monthly_token_cap: opts.monthlyTokenCap ?? null,
      monthly_cost_cap_usd: opts.monthlyCostCapUsd ?? null,
    })
    return r.data?.data ?? r.data
  }

  /** Admin: list all workspace quotas. */
  async list(): Promise<any[]> {
    const r = await this.http.get('/api/v1/admin/quota')
    return r.data?.data ?? []
  }
}
