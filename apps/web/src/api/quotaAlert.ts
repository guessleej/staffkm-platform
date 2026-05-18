import { http } from './index'

export type AlertScope = 'workspace' | 'user'
export type AlertChannel = 'email' | 'slack' | 'webhook'

export interface QuotaAlert {
  id: string
  scope: AlertScope
  threshold_pct: number
  channel: AlertChannel
  target: string
  enabled: boolean
  created_at: string
}

export interface QuotaAlertCreate {
  scope: AlertScope
  threshold_pct: number
  channel: AlertChannel
  target: string
  enabled?: boolean
}

export const quotaAlertApi = {
  list: async (): Promise<QuotaAlert[]> =>
    (await http.get('/quota-alerts')).data.data,
  create: async (body: QuotaAlertCreate): Promise<QuotaAlert> =>
    (await http.post('/quota-alerts', body)).data.data,
  update: async (id: string, body: Partial<QuotaAlertCreate>): Promise<QuotaAlert> =>
    (await http.put(`/quota-alerts/${id}`, body)).data.data,
  delete: async (id: string) => (await http.delete(`/quota-alerts/${id}`)).data,
}
