/**
 * Workspace App Template API client.
 * 後端：services/agent/app/api/app_templates.py
 */
import { http } from './index'

export interface WorkspaceAppTemplate {
  id:                  string
  name:                string
  emoji:               string
  description:         string
  system_prompt:       string
  welcome_message:     string
  suggested_questions: string[]
  requires_kb:         boolean
  created_at:          string
  updated_at:          string
}

export interface CreateAppTemplateInput {
  name:                 string
  emoji?:               string
  description?:         string
  system_prompt?:       string
  welcome_message?:     string
  suggested_questions?: string[]
  requires_kb?:         boolean
}

export type UpdateAppTemplateInput = Partial<CreateAppTemplateInput>

export const appTemplateApi = {
  list: async (): Promise<WorkspaceAppTemplate[]> => {
    const { data } = await http.get('/app-templates')
    return data.data || []
  },
  create: async (body: CreateAppTemplateInput): Promise<{ id: string }> => {
    const { data } = await http.post('/app-templates', body)
    return data.data
  },
  update: async (id: string, body: UpdateAppTemplateInput): Promise<void> => {
    await http.put(`/app-templates/${id}`, body)
  },
  remove: async (id: string): Promise<void> => {
    await http.delete(`/app-templates/${id}`)
  },
}
