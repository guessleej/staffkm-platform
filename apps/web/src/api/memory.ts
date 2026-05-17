/**
 * Long-term Memory API client.
 * 後端：services/agent/app/api/memories.py
 */
import { http } from './index'

export type MemoryScope = 'user' | 'app' | 'team'

export interface Memory {
  id:               string
  user_id:          string | null
  application_id:   string | null
  scope:            MemoryScope
  content:          string
  tags:             string[]
  importance:       number          // 1-10
  access_count:     number
  last_accessed_at: string | null
  created_at:       string
}

export interface CreateMemoryInput {
  content:         string
  scope?:          MemoryScope
  application_id?: string
  tags?:           string[]
  importance?:     number
}

export interface MemoryListResp {
  items:     Memory[]
  page:      number
  page_size: number
}

export const memoryApi = {
  list: async (params: { scope?: MemoryScope; application_id?: string; page?: number; page_size?: number } = {}): Promise<MemoryListResp> => {
    const { data } = await http.get('/memories', { params })
    return data.data || { items: [], page: 1, page_size: 50 }
  },
  create: async (body: CreateMemoryInput): Promise<{ id: string }> => {
    const { data } = await http.post('/memories', body)
    return data.data
  },
  remove: async (id: string): Promise<void> => {
    await http.delete(`/memories/${id}`)
  },
  search: async (body: { query: string; scope?: MemoryScope; application_id?: string; top_k?: number }): Promise<Memory[]> => {
    const { data } = await http.post('/memories/search', body)
    return data.data || []
  },
}
