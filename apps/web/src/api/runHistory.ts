import { http } from './index'

export interface WorkflowRun {
  id: string
  fired_at: string
  finished_at: string | null
  status: string         // 'ok' | 'error' | 'paused' | 'rejected' | 'queued' | 'running' | 'quota_exceeded'
  output_summary: string | null
  error: string | null
  tokens_used: number
  cost_usd: number
  trigger_name: string
}

export interface WorkflowRunStep {
  id: string
  step_index: number
  node_key: string
  node_type: string
  status: string         // 'ok' | 'error' | 'retry' | 'paused'
  input_snapshot: any
  output_snapshot: any
  error: string | null
  attempts: number
  latency_ms: number | null
  started_at: string
  finished_at: string | null
}

export const runHistoryApi = {
  listRuns: async (appId: string, limit = 50): Promise<{ items: WorkflowRun[] }> =>
    (await http.get(`/applications/${appId}/runs?limit=${limit}`)).data.data,
  listSteps: async (appId: string, runId: string): Promise<{ items: WorkflowRunStep[] }> =>
    (await http.get(`/applications/${appId}/runs/${runId}/steps`)).data.data,
}
