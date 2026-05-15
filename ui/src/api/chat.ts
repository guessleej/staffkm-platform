import { http } from './index'

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
): Promise<void> {
  const token = localStorage.getItem('access_token') || ''
  const resp = await fetch(`/api/v1/chat/conversations/${convId}/messages/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ content }),
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
