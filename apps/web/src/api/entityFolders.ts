/**
 * Entity Folders API client（RFC-006 D-5）。
 *
 * 通用 folder API，用 kind 區分用途：app / tool / skill / data_source。
 * KB folders 走 knowledgeApi（C-3 既有），不在此處。
 */
import { http } from './index'

export type EntityKind = 'app' | 'tool' | 'skill' | 'data_source'

export interface EntityFolder {
  id:           string
  workspace_id: string
  entity_kind:  EntityKind
  parent_id:    string | null
  name:         string
  sort_order:   number
  created_at:   string
  updated_at:   string
}

export const entityFolderApi = {
  list: async (kind: EntityKind): Promise<EntityFolder[]> => {
    const { data } = await http.get('/folders', { params: { kind } })
    return data.data || []
  },
  create: async (
    body: { entity_kind: EntityKind; name: string; parent_id?: string | null; sort_order?: number },
  ): Promise<EntityFolder> => {
    const { data } = await http.post('/folders', body)
    return data.data
  },
  update: async (
    id: string,
    patch: Partial<{ name: string; parent_id: string | null; sort_order: number }>,
  ): Promise<EntityFolder> => {
    const { data } = await http.put(`/folders/${id}`, patch)
    return data.data
  },
  remove: async (id: string): Promise<void> => {
    await http.delete(`/folders/${id}`)
  },
}
