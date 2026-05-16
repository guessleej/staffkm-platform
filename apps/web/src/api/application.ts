import { http } from './index'

export interface Application {
  id: string
  name: string
  description: string
  icon?: string
  type: 'simple' | 'workflow'
  status: string
  llm_model_id?: string
  system_prompt?: string
  welcome_message?: string
  suggested_questions: string[]
  knowledge_base_ids: string[]
  config: Record<string, any>
  is_public: boolean
  created_at: string
  updated_at: string
}

export interface ApplicationCreate {
  name: string
  description?: string
  icon?: string
  type?: 'simple' | 'workflow'
  system_prompt?: string
  welcome_message?: string
  suggested_questions?: string[]
  knowledge_base_ids?: string[]
  config?: Record<string, any>
  is_public?: boolean
  llm_model_id?: string
}

export const applicationApi = {
  list(params?: { page?: number; page_size?: number; status?: string }) {
    return http.get('/applications', { params })
  },

  create(data: ApplicationCreate) {
    return http.post('/applications', data)
  },

  get(id: string) {
    return http.get(`/applications/${id}`)
  },

  update(id: string, data: Partial<ApplicationCreate>) {
    return http.put(`/applications/${id}`, data)
  },

  delete(id: string) {
    return http.delete(`/applications/${id}`)
  },

  getSuggestedQuestions(id: string) {
    return http.get(`/applications/${id}/suggested-questions`)
  },

  chat(appId: string, body: { session_id?: string; messages: { role: string; content: string }[]; kb_ids?: string[] }) {
    return `${import.meta.env.VITE_API_BASE_URL || '/api/v1'}/applications/${appId}/chat`
  },
}

// ── Application 版本控制（D-7）─────────────────────────────────────────
export interface AppVersion {
  id: string
  application_id: string
  version_number: number
  note: string | null
  created_at: string
  created_by: string | null
}

export const appVersionApi = {
  async list(appId: string): Promise<AppVersion[]> {
    const r = await http.get(`/applications/${appId}/versions`)
    return r.data?.data ?? []
  },
  async create(appId: string, note?: string): Promise<AppVersion> {
    const r = await http.post(`/applications/${appId}/versions`, { note: note || null })
    return r.data?.data
  },
  async restore(appId: string, versionNumber: number): Promise<AppVersion> {
    const r = await http.post(`/applications/${appId}/versions/${versionNumber}/restore`)
    return r.data?.data
  },
}
