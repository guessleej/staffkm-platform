/** Common types used across resources. */

export interface Workspace {
  id: string
  name: string
  slug?: string
}

export interface KnowledgeBase {
  id: string
  name: string
  description?: string
}

export interface Application {
  id: string
  name: string
  type?: string
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export interface ChatResponse {
  content?: string
  citations?: any[]
  usage?: Record<string, any>
  [k: string]: any
}

export interface QuotaSummary {
  monthly_token_cap?: number | null
  monthly_cost_cap_usd?: number | null
  tokens_used?: number
  cost_used_usd?: number
}
