import { http } from './index'

export interface UserQuotaRow {
  user_id: string
  username: string
  email: string
  monthly_token_cap: number | null
  monthly_cost_cap_usd: number | null
  tokens_used: number
  cost_used: number
}

export const userQuotaApi = {
  list: async (): Promise<{ items: UserQuotaRow[] }> =>
    (await http.get('/user-quotas')).data.data,
  update: async (
    userId: string,
    body: { monthly_token_cap: number | null; monthly_cost_cap_usd: number | null },
  ) => (await http.put(`/user-quotas/${userId}`, body)).data,
}
