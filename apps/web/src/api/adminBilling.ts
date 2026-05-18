import { http } from './index'

export interface UserBillingRow {
  user_id: string
  username: string
  email: string
  workspace_name: string | null
  workspace_id: string
  calls: number
  tokens: number
  cost: number
  conversations: number
}

export interface UserBillingSummary {
  total_cost: number
  total_tokens: number
  user_count: number
}

export interface UserBillingDetail {
  month: string
  by_feature: Array<{ feature: string; calls: number; tokens: number; cost: number }>
  top_conversations: Array<{ conversation_id: string; calls: number; tokens: number; cost: number; started_at: string }>
  daily: Array<{ day: string; calls: number; tokens: number; cost: number }>
}

export const adminBillingApi = {
  list: async (month?: string): Promise<{ month: string; items: UserBillingRow[]; summary: UserBillingSummary }> => {
    const q = month ? `?month=${month}` : ''
    return (await http.get(`/admin/billing/users${q}`)).data.data
  },
  detail: async (userId: string, month?: string): Promise<UserBillingDetail> => {
    const q = month ? `?month=${month}` : ''
    return (await http.get(`/admin/billing/users/${userId}${q}`)).data.data
  },
  csvUrl: (month?: string) => {
    const q = month ? `?month=${month}` : ''
    return `/api/v1/admin/billing/users.csv${q}`
  },
}
