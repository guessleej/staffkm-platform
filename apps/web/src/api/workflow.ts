import { http } from './index'

export interface WorkflowNode {
  id: string
  node_key: string
  node_type: 'start' | 'llm' | 'knowledge_retrieval' | 'condition' | 'variable' | 'http_request' | 'answer' | 'loop' | 'loop_break' | 'intent' | 'parameter_extraction' | 'reranker' | 'speech_to_text' | 'text_to_speech' | 'image_understand' | 'image_generate' | 'document_extract' | 'document_split' | 'form' | 'mcp_tool'
  label: string
  config: Record<string, any>
  position: { x: number; y: number }
}

export interface WorkflowEdge {
  id: string
  source_node_key: string
  target_node_key: string
  condition?: any
}

export interface WorkflowVersion {
  id:             string
  application_id: string
  version_number: number
  note:           string | null
  created_at:     string
  created_by:     string | null
}

export const workflowApi = {
  get: (appId: string) =>
    http.get<{ data: { data: { nodes: WorkflowNode[]; edges: WorkflowEdge[] } } }>(
      `/applications/${appId}/workflow`
    ),
  save: (appId: string, data: { nodes: WorkflowNode[]; edges: WorkflowEdge[] }) =>
    http.post(`/applications/${appId}/workflow`, data),
  chatUrl: (appId: string) => `/api/v1/applications/${appId}/workflow/chat`,
  // Sprint 19 — Workflow Versions
  async listVersions(appId: string): Promise<WorkflowVersion[]> {
    const { data } = await http.get(`/applications/${appId}/workflow/versions`)
    return data.data || []
  },
  async createVersion(appId: string, note?: string): Promise<WorkflowVersion> {
    const { data } = await http.post(`/applications/${appId}/workflow/versions`, { note })
    return data.data
  },
  async restoreVersion(appId: string, versionNumber: number): Promise<WorkflowVersion> {
    const { data } = await http.post(`/applications/${appId}/workflow/versions/${versionNumber}/restore`)
    return data.data
  },
}
