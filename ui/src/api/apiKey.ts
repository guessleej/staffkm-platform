import { http } from './index'

export interface ApiKey {
  id: string
  name: string
  application_id: string
  key_prefix: string
  is_active: boolean
  created_at: string
  expires_at: string | null
  last_used_at: string | null
  full_key?: string  // 只在建立時有
}

export const apiKeyApi = {
  list: (appId?: string) =>
    http.get<{ data: { data: ApiKey[] } }>('/api-keys', { params: appId ? { application_id: appId } : {} }),
  create: (data: { name: string; application_id: string; expires_days?: number }) =>
    http.post<{ data: { data: ApiKey } }>('/api-keys', data),
  remove: (id: string) => http.delete(`/api-keys/${id}`),
  toggle: (id: string) => http.patch(`/api-keys/${id}/toggle`),
}
