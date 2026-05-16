import { http } from './index'

export interface Project {
  id:                   string
  workspace_id:         string
  name:                 string
  description?:         string | null
  emoji?:               string | null
  system_prompt?:       string | null
  knowledge_base_ids:   string[]
  application_ids:      string[]
  created_at:           string
  updated_at:           string
  created_by?:          string | null
  updated_by?:          string | null
}

export interface CreateProjectInput {
  name:           string
  description?:   string
  emoji?:         string
  system_prompt?: string
}

export type UpdateProjectInput = Partial<CreateProjectInput>

export type ResourceKind = 'kb' | 'app'

export const projectApi = {
  list: async (): Promise<Project[]> => {
    const { data } = await http.get('/projects')
    return data.data || []
  },
  get: async (id: string): Promise<Project> => {
    const { data } = await http.get(`/projects/${id}`)
    return data.data
  },
  create: async (body: CreateProjectInput): Promise<Project> => {
    const { data } = await http.post('/projects', body)
    return data.data
  },
  update: async (id: string, body: UpdateProjectInput): Promise<Project> => {
    const { data } = await http.put(`/projects/${id}`, body)
    return data.data
  },
  remove: async (id: string): Promise<void> => {
    await http.delete(`/projects/${id}`)
  },
  attachResource: async (id: string, kind: ResourceKind, resourceId: string): Promise<Project> => {
    const { data } = await http.post(`/projects/${id}/resources`, { kind, resource_id: resourceId })
    return data.data
  },
  detachResource: async (id: string, kind: ResourceKind, resourceId: string): Promise<Project> => {
    const { data } = await http.delete(`/projects/${id}/resources/${kind}/${resourceId}`)
    return data.data
  },
}
