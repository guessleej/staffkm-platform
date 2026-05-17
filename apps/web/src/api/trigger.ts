/**
 * Event Trigger API client.
 * 後端：services/agent/app/api/triggers.py
 */
import { http } from './index'

export type TriggerKind = 'interval' | 'cron' | 'webhook'
export type RunStatus = 'pending' | 'running' | 'ok' | 'failed' | 'cancelled' | null

export interface Trigger {
  id:              string
  application_id:  string
  name:            string
  kind:            TriggerKind
  cron_expr:       string | null
  interval_sec:    number | null
  enabled:         boolean
  next_fire_at:    string | null
  last_fired_at:   string | null
  last_status:     RunStatus
  last_error:      string | null
  created_at:      string
  updated_at:      string
}

export interface TriggerRun {
  id:              string
  fired_at:        string
  finished_at:     string | null
  status:          RunStatus
  output_summary:  string | null
  error:           string | null
}

export interface CreateTriggerInput {
  application_id:  string
  name:            string
  kind?:           TriggerKind
  cron_expr?:      string
  interval_sec?:   number
  input_template?: string
  enabled?:        boolean
}

export type UpdateTriggerInput = Partial<{
  name:           string
  cron_expr:      string | null
  interval_sec:   number | null
  input_template: string
  enabled:        boolean
}>

export const triggerApi = {
  list: async (): Promise<Trigger[]> => {
    const { data } = await http.get('/triggers')
    return data.data || []
  },
  create: async (body: CreateTriggerInput): Promise<{ id: string }> => {
    const { data } = await http.post('/triggers', body)
    return data.data
  },
  update: async (id: string, body: UpdateTriggerInput): Promise<void> => {
    await http.put(`/triggers/${id}`, body)
  },
  remove: async (id: string): Promise<void> => {
    await http.delete(`/triggers/${id}`)
  },
  listRuns: async (id: string): Promise<TriggerRun[]> => {
    const { data } = await http.get(`/triggers/${id}/runs`)
    return data.data || []
  },
}
