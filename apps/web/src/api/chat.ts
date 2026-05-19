import { http } from './index'

// v2.7：分享對話 / 讀公開對話
export const shareApi = {
  share: async (convId: string): Promise<{ share_token: string }> => {
    const { data } = await http.post(`/chat/conversations/${convId}/share`)
    return data.data
  },
  revoke: async (convId: string): Promise<void> => {
    await http.delete(`/chat/conversations/${convId}/share`)
  },
  /** 公開讀取（無需 JWT）— 透過 gateway PUBLIC_PREFIXES 直接讀 chat service */
  getPublic: async (token: string) => {
    const { data } = await fetch(`/api/v1/public/conversations/${token}`).then(r => r.json())
    return data
  },
}

export const chatApi = {
  async listConversations(page = 1) {
    const { data } = await http.get('/chat/conversations', { params: { page } })
    return data
  },
  async createConversation(scenarioId: string, kbIds: string[] = []) {
    const { data } = await http.post('/chat/conversations', { scenario_id: scenarioId, kb_ids: kbIds })
    return data.data
  },
  async getMessages(convId: string) {
    const { data } = await http.get(`/chat/conversations/${convId}/messages`)
    return data.data
  },
  async deleteConversation(convId: string) {
    await http.delete(`/chat/conversations/${convId}`)
  },
  streamMessage(convId: string, content: string): EventSource {
    const token = localStorage.getItem('access_token') || ''
    // 使用 fetch SSE
    const url = `/api/v1/chat/conversations/${convId}/messages/stream`
    return { url, content, token } as unknown as EventSource
  },
}

export async function streamChat(
  convId: string,
  content: string,
  onToken: (t: string) => void,
  onCitations: (c: unknown[]) => void,
  onDone: () => void,
  onError: (e: string) => void,
  /** v2.8: 對話中動態切 model / KB（不改 application 預設） */
  overrides?: { model_override?: string | null; kb_ids_override?: string[] | null },
): Promise<void> {
  const token = localStorage.getItem('access_token') || ''
  const payload: Record<string, unknown> = { content }
  if (overrides?.model_override) payload.model_override = overrides.model_override
  if (overrides?.kb_ids_override) payload.kb_ids_override = overrides.kb_ids_override
  const resp = await fetch(`/api/v1/chat/conversations/${convId}/messages/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  })

  if (!resp.ok || !resp.body) {
    onError(`HTTP ${resp.status}`)
    return
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (line.startsWith('event:')) continue
      if (line.startsWith('data:')) {
        const data = line.slice(5).trim()
        if (!data || data === '[DONE]') { onDone(); continue }
        try {
          const parsed = JSON.parse(data)
          if (Array.isArray(parsed)) { onCitations(parsed); continue }
        } catch { /* token text */ }
        onToken(data)
      }
    }
  }
}

// Sprint 19-B：模板 preview 串流（無持久化、不計 usage）
export async function streamPreviewChat(
  body: {
    messages: { role: 'user' | 'assistant'; content: string }[]
    system_prompt?: string
    welcome_message?: string
    llm_model_id?: string
    kb_ids?: string[]
  },
  onToken: (t: string) => void,
  onDone: () => void,
  onError: (e: string) => void,
): Promise<void> {
  const token = localStorage.getItem('access_token') || ''
  const resp = await fetch('/api/v1/applications/preview/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  })
  if (!resp.ok || !resp.body) { onError(`HTTP ${resp.status}`); return }
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      if (line.startsWith('event:')) continue
      if (line.startsWith('data:')) {
        const data = line.slice(5).trim()
        if (!data || data === '[DONE]') { onDone(); continue }
        try {
          const parsed = JSON.parse(data)
          if (Array.isArray(parsed)) continue  // citations — preview 不顯示
        } catch { /* token text */ }
        onToken(data)
      }
    }
  }
}
