import { http } from './index'

export interface WorkspaceQuotaRow {
  workspace_id:         string
  workspace_name:       string
  monthly_token_cap:    number | null
  monthly_cost_cap_usd: number | null
  tokens_used:          number
  cost_used:            number
}

export const adminQuotaApi = {
  async list(): Promise<{ items: WorkspaceQuotaRow[]; month: string }> {
    const r = await http.get('/admin/quotas')
    return r.data?.data
  },

  async update(
    workspaceId: string,
    body: { monthly_token_cap: number | null; monthly_cost_cap_usd: number | null },
  ) {
    const r = await http.put(`/admin/quotas/${workspaceId}`, body)
    return r.data
  },
}
