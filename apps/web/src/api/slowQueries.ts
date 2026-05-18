import { http } from './index'

export interface SlowQueryRow {
  id: string
  captured_at: string
  duration_ms: number
  sql_text: string
  sql_hash: string
  explain_error: string | null
  has_plan: boolean
}

export interface SlowQueryDetail extends SlowQueryRow {
  explain_json: any | null
}

export interface SlowQueryAggregate {
  sql_hash: string
  occurrences: number
  max_ms: number
  avg_ms: number
  sample_sql: string
}

export const slowQueriesApi = {
  list:    async (): Promise<{ items: SlowQueryRow[] }> => (await http.get('/admin/slow-queries')).data.data,
  detail:  async (id: string): Promise<SlowQueryDetail> => (await http.get(`/admin/slow-queries/${id}`)).data.data,
  topByHash: async (): Promise<{ items: SlowQueryAggregate[] }> => (await http.get('/admin/slow-queries/top-by-hash')).data.data,
}
