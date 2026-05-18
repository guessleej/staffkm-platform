import { http } from './index'

export interface UsageByDay {
  day:      string
  tokens:   number
  cost_usd: number
}

export interface UsageByModel {
  model:    string
  tokens:   number
  cost_usd: number
  requests: number
}

export interface UsageSummary {
  month:     string
  usage:     { tokens: number; cost_usd: number; requests: number }
  quota:     { monthly_token_cap: number | null; monthly_cost_cap_usd: number | null }
  by_day?:   UsageByDay[]
  by_model?: UsageByModel[]
}

export interface UsageLog {
  id:               string
  user_id:          string | null
  application_id:   string | null
  provider_type:    string | null
  model:            string | null
  prompt_tokens:    number
  completion_tokens:number
  total_tokens:     number
  cost_usd:         number
  latency_ms:       number
  status:           string
  error:            string | null
  created_at:       string
}

export const usageApi = {
  async summary(): Promise<UsageSummary> {
    const r = await http.get('/usage/summary')
    return r.data?.data
  },
  async logs(page = 1, page_size = 50): Promise<{ items: UsageLog[]; page: number; page_size: number }> {
    const r = await http.get('/usage/logs', { params: { page, page_size } })
    return r.data?.data
  },
  async getQuota(): Promise<{ monthly_token_cap: number | null; monthly_cost_cap_usd: number | null }> {
    const r = await http.get('/usage/quota')
    return r.data?.data
  },
  async setQuota(body: { monthly_token_cap?: number | null; monthly_cost_cap_usd?: number | null }) {
    const r = await http.put('/usage/quota', body)
    return r.data?.data
  },
}
