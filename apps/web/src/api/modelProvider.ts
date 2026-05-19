import { http } from './index'

export interface ModelProvider {
  id: string
  name: string
  provider_type: 'openai' | 'ollama' | 'azure' | 'anthropic' | 'custom'
  base_url?: string
  api_key_masked?: string
  status: string
  config: Record<string, any>
  created_at: string
}

export interface AiModel {
  id: string
  provider_id: string
  model_name: string
  model_type: 'llm' | 'embedding' | 'reranker' | 'tts' | 'stt'
  display_name?: string
  config: Record<string, any>
  is_default: boolean
  status: string
}

export const modelProviderApi = {
  listProviders(params?: { page?: number; page_size?: number }) {
    return http.get('/admin/models/providers', { params })
  },

  createProvider(data: { name: string; provider_type: string; base_url?: string; api_key?: string; config?: Record<string, any> }) {
    return http.post('/admin/models/providers', data)
  },

  getProvider(id: string) {
    return http.get(`/admin/models/providers/${id}`)
  },

  updateProvider(id: string, data: Partial<{ name: string; base_url: string; api_key: string; config: Record<string, any>; status: string }>) {
    return http.put(`/admin/models/providers/${id}`, data)
  },

  deleteProvider(id: string) {
    return http.delete(`/admin/models/providers/${id}`)
  },

  verifyProvider(id: string) {
    return http.post(`/admin/models/providers/${id}/verify`)
  },

  listModels(providerId?: string, modelType?: string) {
    if (providerId) {
      return http.get(`/admin/models/providers/${providerId}/models`)
    }
    return http.get('/admin/models/models', { params: { model_type: modelType } })
  },

  createModel(providerId: string, data: { model_name: string; model_type: string; display_name?: string; config?: Record<string, any>; is_default?: boolean }) {
    return http.post(`/admin/models/providers/${providerId}/models`, data)
  },

  updateModel(modelId: string, data: Partial<{ display_name: string; config: Record<string, any>; is_default: boolean; status: string }>) {
    return http.put(`/admin/models/models/${modelId}`, data)
  },

  deleteModel(modelId: string) {
    return http.delete(`/admin/models/models/${modelId}`)
  },
}

// ── Model Provider Registry（M3 中段-C）───────────────────────────────
export interface ProviderRegistryEntry {
  type:                string
  label:               string
  adapter_type:        string
  default_base_url:    string | null
  recommended_models:  string[]
  needs_api_key:       boolean
  notes:               string
  capabilities:        string[]   // v5.0.6: LLM / Embedding / Reranker / TTS / STT / Vision / Image / Moderation
  is_local:            boolean    // v5.0.6: 地端 self-host (catalog chip)
}

export const providerRegistryApi = {
  async list(): Promise<ProviderRegistryEntry[]> {
    const r = await http.get('/model-providers/registry')
    return r.data?.data ?? []
  },
}
