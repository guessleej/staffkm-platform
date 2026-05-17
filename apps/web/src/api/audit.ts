/**
 * Audit log API client (admin only).
 * 後端：services/agent/app/api/audit.py
 */
import { http } from './index'

export interface AuditLog {
  id:              string
  actor_user_id:   string | null
  actor_username:  string | null
  action:          string
  entity_type:     string
  entity_id:       string | null
  entity_label:    string | null
  detail:          Record<string, unknown>
  ip_address:      string | null
  user_agent:      string | null
  created_at:      string
}

export interface AuditListResp {
  items: AuditLog[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export const auditApi = {
  list: async (params: {
    actor?: string;
    action?: string;
    entity?: string;
    since?: string;
    page?: number;
    page_size?: number;
  } = {}): Promise<AuditListResp> => {
    const { data } = await http.get('/admin/audit-logs', { params })
    return {
      items:       data.data || [],
      total:       data.meta?.total ?? 0,
      page:        data.meta?.page ?? 1,
      page_size:   data.meta?.page_size ?? 50,
      total_pages: data.meta?.total_pages ?? 1,
    }
  },
}
