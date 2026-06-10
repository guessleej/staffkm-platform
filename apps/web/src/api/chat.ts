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
  async listConversations(page = 1, pageSize = 200) {   // v5.12: 提高避免側欄對話 >20 筆靜默截斷
    const { data } = await http.get('/chat/conversations', { params: { page, page_size: pageSize } })
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
  /** v5.10.14: 應用對話的 function-calling 工具呼叫過程（折疊式 UI） */
  onToolCall?: (tc: { name: string; status?: string; input?: unknown; output?: unknown; error?: string | null }) => void,
): Promise<void> {
  const token = localStorage.getItem('access_token') || ''
  const payload: Record<string, unknown> = { content }
  if (overrides?.model_override) payload.model_override = overrides.model_override
  if (overrides?.kb_ids_override) payload.kb_ids_override = overrides.kb_ids_override
  // v5.9.14: 必須帶 X-Workspace-ID — 之前漏，chat 內部 call agent 沒 ws prefix → 404 → empty stream
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  }
  try {
    const { useWorkspaceStore } = await import('../stores/workspace')
    const store = useWorkspaceStore()
    if (!store.currentId) await store.ensureReady()   // v5.13 race 修：workspace 就緒才送
    const wsId = store.currentId
    if (wsId) headers['X-Workspace-ID'] = wsId
  } catch { /* store 未 init */ }
  const resp = await fetch(`/api/v1/chat/conversations/${convId}/messages/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  })

  if (!resp.ok || !resp.body) {
    onError(`HTTP ${resp.status}`)
    return
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let evType = ''
  let dataLines: string[] = []

  // v5.10.13/14: SSE 多行 data 用 \n 重組（token 含換行被 sse-starlette 拆成多行）；
  // 追蹤 event: 型別 → token / citations / tool_call 正確分派（應用對話會帶 tool_call）。
  const flush = () => {
    if (!evType && dataLines.length === 0) return
    const data = dataLines.join('\n')
    const ev = evType
    evType = ''
    dataLines = []
    if (ev === 'tool_call') {
      try { onToolCall?.(JSON.parse(data)) } catch { /* ignore */ }
      return
    }
    if (ev === 'citations') {
      try { const p = JSON.parse(data); if (Array.isArray(p)) onCitations(p) } catch { /* ignore */ }
      return
    }
    const trimmed = data.trim()
    // 只在明確的 done 訊號結束串流。v5.11.6 根因：之前用 `!trimmed` 當 done →
    // 純換行 token（data="\n\n"）的 trimmed 為空 → 被當結束 + 換行被丟 → 答案擠成一坨。
    if (ev === 'done' || trimmed === '[DONE]') { onDone(); return }
    if (ev === 'error') { onError(data); return }
    if (data === '') return  // 真正空事件（keep-alive/邊界）跳過；純換行 token（data 非空）保留
    // token（或無 event: 標記）：內容是 list → citations（相容 agents 端）
    try {
      const parsed = JSON.parse(trimmed)
      if (Array.isArray(parsed)) { onCitations(parsed); return }
    } catch { /* token text */ }
    onToken(data)
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const raw of lines) {
      const line = raw.replace(/\r$/, '')              // 去 CRLF 尾 \r
      if (line === '') { flush(); continue }            // event 邊界
      if (line.startsWith('event:')) { evType = line.slice(6).replace(/^ /, '').trim(); continue }
      if (line.startsWith('data:')) {
        // 去 "data:" + 一個 SSE 分隔空格（保留 token 真正的前導空格，如 " RTX"）
        dataLines.push(line.slice(5).replace(/^ /, ''))
      }
    }
  }
  flush()
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
  // v5.9.14: streamPreviewChat 同樣需要 X-Workspace-ID
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  }
  try {
    const { useWorkspaceStore } = await import('../stores/workspace')
    const store = useWorkspaceStore()
    if (!store.currentId) await store.ensureReady()   // v5.13 race 修：workspace 就緒才送
    const wsId = store.currentId
    if (wsId) headers['X-Workspace-ID'] = wsId
  } catch { /* store 未 init */ }
  const resp = await fetch('/api/v1/applications/preview/chat', {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  })
  if (!resp.ok || !resp.body) { onError(`HTTP ${resp.status}`); return }
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let dataLines: string[] = []

  // v5.10.13: 同 streamChat — 多行 data 用 \n 重組，遇空行才分派
  const flush = () => {
    if (dataLines.length === 0) return
    const data = dataLines.join('\n')
    dataLines = []
    const trimmed = data.trim()
    if (trimmed === '[DONE]') { onDone(); return }   // 只認明確 done；純換行 token 不可當結束
    if (data === '') return                          // 真正空事件跳過；純換行（data 非空）保留
    try {
      const parsed = JSON.parse(trimmed)
      if (Array.isArray(parsed)) return  // citations — preview 不顯示
    } catch { /* token text */ }
    onToken(data)
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const raw of lines) {
      const line = raw.replace(/\r$/, '')
      if (line === '') { flush(); continue }
      if (line.startsWith('event:')) continue
      if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).replace(/^ /, ''))
      }
    }
  }
  flush()
}
