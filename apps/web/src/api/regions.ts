// v5.0 K: active-active multi-region admin API
import { http } from './index'

export interface Region {
  id: string
  name: string
  db_url?: string | null
  minio_endpoint?: string | null
  is_active: boolean
  created_at: string
}

export interface ConflictRow {
  id: string
  detected_at: string
  entity_type: string
  entity_id: string
  region_a: string
  region_b: string
  value_a: unknown
  value_b: unknown
  resolution: string | null
  resolved_value: unknown
  resolved_at: string | null
}

export const regionsApi = {
  list: async (): Promise<{ items: Region[] }> =>
    (await http.get('/admin/regions')).data.data,

  create: (body: {
    id: string
    name: string
    db_url?: string
    minio_endpoint?: string
  }) => http.post('/admin/regions', body),

  deactivate: (regionId: string) => http.delete(`/admin/regions/${regionId}`),

  listConflicts: async (status?: 'pending' | 'resolved'): Promise<{ items: ConflictRow[] }> => {
    const q = status ? `?status=${status}` : ''
    return (await http.get(`/admin/conflicts${q}`)).data.data
  },

  resolveConflict: (id: string, body: { resolution: 'lww' | 'merge' | 'manual'; resolved_value?: unknown }) =>
    http.post(`/admin/conflicts/${id}/resolve`, body),

  bindWorkspace: (wsId: string, primaryRegion: string) =>
    http.put(`/admin/workspaces/${wsId}/region`, { primary_region: primaryRegion }),
}
