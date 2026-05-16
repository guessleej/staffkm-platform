/**
 * Tools / Skills / Data Sources 三個 backlog 模組共用的精簡 API client。
 *
 * 三個都走相同的 workspace-scoped CRUD 模式（agent service /tools /skills
 * /data-sources），共用泛型工廠以避免重複。
 */
import { http } from './index'

export interface BaseEntity {
  id:           string
  workspace_id: string
  name:         string
  description?: string | null
  created_at:   string
  updated_at:   string
}

export interface ToolEntity extends BaseEntity {
  kind:       string                  // 'http' | 'mcp' | 'shell' | 'custom'
  config:     Record<string, unknown>
  is_enabled: boolean
}

export interface SkillEntity extends BaseEntity {
  prompt_template: string
  variables:       Array<Record<string, unknown>>
  tags:            string[]
}

export interface DataSourceEntity extends BaseEntity {
  kind:           string              // 'postgres' | 'mysql' | 'rest' | ...
  config:         Record<string, unknown>
  is_enabled:     boolean
  last_synced_at: string | null
}

function makeCrud<T extends BaseEntity, C, U>(prefix: string) {
  return {
    list:   async (): Promise<T[]> => (await http.get(`/${prefix}`)).data.data || [],
    get:    async (id: string): Promise<T> => (await http.get(`/${prefix}/${id}`)).data.data,
    create: async (body: C): Promise<T> => (await http.post(`/${prefix}`, body)).data.data,
    update: async (id: string, body: U): Promise<T> => (await http.put(`/${prefix}/${id}`, body)).data.data,
    remove: async (id: string): Promise<void> => { await http.delete(`/${prefix}/${id}`) },
  }
}

export interface ToolExecResult {
  success:    boolean
  status:     number | null
  output:     Record<string, unknown> | null
  text:       string | null
  elapsed_ms: number
  error?:     string | null
}

export const toolApi = {
  ...makeCrud<ToolEntity, Partial<ToolEntity>, Partial<ToolEntity>>('tools'),
  execute: async (id: string, inputs: Record<string, unknown>): Promise<ToolExecResult> => {
    const { data } = await http.post(`/tools/${id}/execute`, { inputs })
    return data.data
  },
}
export const skillApi       = makeCrud<SkillEntity, Partial<SkillEntity>, Partial<SkillEntity>>('skills')
export interface DataSourceTestResult {
  success:    boolean
  elapsed_ms: number
  detail:     string
  config_ok:  boolean
  missing:    string[]
}

export const dataSourceApi = {
  ...makeCrud<DataSourceEntity, Partial<DataSourceEntity>, Partial<DataSourceEntity>>('data-sources'),
  test: async (id: string): Promise<DataSourceTestResult> => {
    const { data } = await http.post(`/data-sources/${id}/test`)
    return data.data
  },
}
