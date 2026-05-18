import { AxiosInstance } from 'axios'

class BillingUsers {
  constructor(private http: AxiosInstance) {}

  async list(month?: string): Promise<any[]> {
    const r = await this.http.get('/api/v1/billing/users', { params: month ? { month } : {} })
    return r.data?.data ?? []
  }

  async detail(userId: string, month?: string): Promise<any> {
    const r = await this.http.get(`/api/v1/billing/users/${userId}`, {
      params: month ? { month } : {},
    })
    return r.data?.data ?? r.data
  }

  async csv(month?: string): Promise<string> {
    const r = await this.http.get('/api/v1/billing/users.csv', {
      params: month ? { month } : {},
      responseType: 'text',
    })
    return r.data as string
  }
}

export class BillingResource {
  users: BillingUsers
  constructor(http: AxiosInstance) {
    this.users = new BillingUsers(http)
  }
}
