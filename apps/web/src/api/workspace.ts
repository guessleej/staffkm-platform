import { http } from './index'

export interface Workspace {
  id: string
  name: string
  slug: string
  description: string | null
  plan: string
  role: 'owner' | 'admin' | 'editor' | 'viewer' | null
  member_count: number
  created_at: string
}

export interface WorkspaceMember {
  user_id: string
  username: string | null
  display_name: string | null
  email: string | null
  role: 'owner' | 'admin' | 'editor' | 'viewer'
  joined_at: string | null
  invited_at: string
  is_active: boolean
}

export interface CreateWorkspaceInput {
  name: string
  slug: string
  description?: string
}

export interface UpdateWorkspaceInput {
  name?: string
  description?: string
}

export const workspaceApi = {
  list: async (): Promise<Workspace[]> => {
    const { data } = await http.get('/workspaces')
    return data.data
  },
  get: async (id: string): Promise<Workspace> => {
    const { data } = await http.get(`/workspaces/${id}`)
    return data.data
  },
  create: async (body: CreateWorkspaceInput): Promise<Workspace> => {
    const { data } = await http.post('/workspaces', body)
    return data.data
  },
  update: async (id: string, body: UpdateWorkspaceInput): Promise<Workspace> => {
    const { data } = await http.patch(`/workspaces/${id}`, body)
    return data.data
  },
  remove: async (id: string): Promise<void> => {
    await http.delete(`/workspaces/${id}`)
  },
  listMembers: async (id: string): Promise<WorkspaceMember[]> => {
    const { data } = await http.get(`/workspaces/${id}/members`)
    return data.data
  },
  invite: async (id: string, userId: string, role: WorkspaceMember['role'] = 'viewer'): Promise<WorkspaceMember> => {
    const { data } = await http.post(`/workspaces/${id}/members`, { user_id: userId, role })
    return data.data
  },
  updateMemberRole: async (id: string, userId: string, role: WorkspaceMember['role']): Promise<WorkspaceMember> => {
    const { data } = await http.patch(`/workspaces/${id}/members/${userId}`, { role })
    return data.data
  },
  removeMember: async (id: string, userId: string): Promise<void> => {
    await http.delete(`/workspaces/${id}/members/${userId}`)
  },
}

export const DEFAULT_WORKSPACE_ID = '00000000-0000-0000-0000-000000000001'
