/**
 * MCP (Model Context Protocol) Server API client.
 * 後端：services/agent/app/api/mcp_servers.py，gateway exposed as /mcp/*
 */
import { http } from './index'

export interface McpServer {
  id:                 string
  name:               string
  description:        string | null
  transport:          'http' | 'sse' | 'stdio'
  url:                string | null
  enabled:            boolean
  last_refreshed_at:  string | null
  last_error:         string | null
  created_at:         string
  updated_at:         string
}

export interface McpTool {
  id:           string
  name:         string
  description:  string | null
  input_schema: Record<string, unknown>
  refreshed_at: string
}

export interface CreateServerInput {
  name:         string
  description?: string
  transport?:   'http' | 'sse'
  url?:         string
  enabled?:     boolean
}

export type UpdateServerInput = Partial<{
  name:        string
  description: string | null
  url:         string
  enabled:     boolean
}>

export const mcpApi = {
  list: async (): Promise<McpServer[]> => {
    const { data } = await http.get('/mcp/servers')
    return data.data || []
  },
  create: async (body: CreateServerInput): Promise<{ id: string }> => {
    const { data } = await http.post('/mcp/servers', body)
    return data.data
  },
  update: async (id: string, body: UpdateServerInput): Promise<void> => {
    await http.put(`/mcp/servers/${id}`, body)
  },
  remove: async (id: string): Promise<void> => {
    await http.delete(`/mcp/servers/${id}`)
  },
  refresh: async (id: string): Promise<{ count: number }> => {
    const { data } = await http.post(`/mcp/servers/${id}/refresh`)
    return data.data
  },
  listTools: async (id: string): Promise<McpTool[]> => {
    const { data } = await http.get(`/mcp/servers/${id}/tools`)
    return data.data || []
  },
  callTool: async (
    id: string,
    tool: string,
    args: Record<string, unknown> = {},
  ): Promise<unknown> => {
    const { data } = await http.post(`/mcp/servers/${id}/call`, { tool, arguments: args })
    return data.data
  },
}
