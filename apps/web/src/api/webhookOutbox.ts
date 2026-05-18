import { http } from './index'

export interface WebhookOutboxRow {
  id: string
  url: string
  method: string
  status: 'pending' | 'in_flight' | 'delivered' | 'failed'
  attempts: number
  next_retry_at: string
  last_error: string | null
  last_status_code: number | null
  source_type: string | null
  source_id: string | null
  workspace_id: string | null
  created_at: string
  delivered_at: string | null
}

export const webhookOutboxApi = {
  list: async (status?: string): Promise<{ items: WebhookOutboxRow[] }> => {
    const q = status ? `?status=${status}` : ''
    return (await http.get(`/admin/webhook-outbox${q}`)).data.data
  },
  retry: (id: string) => http.post(`/admin/webhook-outbox/${id}/retry`),
}
