import { defineStore } from 'pinia'
import { ref } from 'vue'
import { http } from '../api/index'

export interface ToolCall {
  /** function name / tool name */
  name: string
  /** invocation status：running 中、success 已完成、error 失敗 */
  status: 'running' | 'success' | 'error'
  /** LLM 傳給 tool 的 args（JSON） */
  input?: Record<string, unknown> | null
  /** tool runtime 回的結果 */
  output?: unknown
  /** 失敗訊息 */
  error?: string | null
}

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  citations: Citation[]
  created_at: string
  streaming?: boolean
  /** MaxKB v2.7：function-calling 工具呼叫紀錄（折疊式 UI） */
  tool_calls?: ToolCall[]
}

export interface Citation {
  doc_name: string
  content: string
  score: number
  paragraph_id?: string
}

export interface Conversation {
  id: string
  title: string
  scenario_id?: string | null
  // v5.10.14：對話可綁應用（application）而非代理人（scenario）
  application_id?: string | null
  message_count: number
  updated_at: string
}

export const useConversationStore = defineStore('conversation', () => {
  const conversations = ref<Conversation[]>([])
  const currentConversation = ref<Conversation | null>(null)
  const messages = ref<Message[]>([])
  const loading = ref(false)
  const streaming = ref(false)

  async function fetchConversations(scenarioId?: string) {
    const params = scenarioId ? { scenario_id: scenarioId } : {}
    const { data } = await http.get('/chat/conversations', { params })
    conversations.value = data.data?.items ?? data.data ?? []
    return conversations.value
  }

  async function fetchMessages(conversationId: string) {
    loading.value = true
    try {
      const { data } = await http.get(`/chat/conversations/${conversationId}/messages`)
      messages.value = data.data ?? []
      return messages.value
    } finally {
      loading.value = false
    }
  }

  async function createConversation(scenarioId: string, title?: string, kbIds?: string[]) {
    const { data } = await http.post('/chat/conversations', {
      scenario_id: scenarioId,
      title: title || '新對話',
      kb_ids: kbIds ?? [],
    })
    // v5.9.11: 後端回 {conversation_id, title}，但前端到處用 conv.id
    // → 統一 normalize 成 {id, scenario_id, ...} 補齊 Conversation interface
    const raw = data.data || {}
    const conv: Conversation = {
      id: raw.id || raw.conversation_id,
      title: raw.title || title || '新對話',
      scenario_id: raw.scenario_id ?? scenarioId,
      message_count: raw.message_count ?? 0,
      updated_at: raw.updated_at || new Date().toISOString(),
    }
    conversations.value.unshift(conv)
    currentConversation.value = conv
    messages.value = []
    return conv
  }

  // v5.10.14：建立綁定「應用」的對話（統一進對話清單，取代獨立 ApplicationChatView）
  async function createApplicationConversation(appId: string, title?: string, kbIds?: string[]) {
    const { data } = await http.post('/chat/conversations', {
      application_id: appId,
      title: title || '新對話',
      kb_ids: kbIds ?? [],
    })
    const raw = data.data || {}
    const conv: Conversation = {
      id: raw.id || raw.conversation_id,
      title: raw.title || title || '新對話',
      scenario_id: null,
      application_id: raw.application_id ?? appId,
      message_count: raw.message_count ?? 0,
      updated_at: raw.updated_at || new Date().toISOString(),
    }
    conversations.value.unshift(conv)
    currentConversation.value = conv
    messages.value = []
    return conv
  }

  async function deleteConversation(id: string) {
    await http.delete(`/chat/conversations/${id}`)
    conversations.value = conversations.value.filter(c => c.id !== id)
    if (currentConversation.value?.id === id) {
      currentConversation.value = null
      messages.value = []
    }
  }

  function selectConversation(conv: Conversation) {
    currentConversation.value = conv
    messages.value = []
  }

  function addUserMessage(content: string): Message {
    const msg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      citations: [],
      created_at: new Date().toISOString(),
    }
    messages.value.push(msg)
    return msg
  }

  function startAssistantMessage(): Message {
    const msg: Message = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      citations: [],
      created_at: new Date().toISOString(),
      streaming: true,
    }
    messages.value.push(msg)
    return msg
  }

  function appendToken(msgId: string, token: string) {
    const msg = messages.value.find(m => m.id === msgId)
    if (msg) msg.content += token
  }

  /** MaxKB v2.7：append 一筆 function-calling 工具呼叫紀錄到訊息 */
  function appendToolCall(msgId: string, call: ToolCall) {
    const msg = messages.value.find(m => m.id === msgId)
    if (!msg) return
    if (!msg.tool_calls) msg.tool_calls = []
    msg.tool_calls.push(call)
  }

  function finishAssistantMessage(msgId: string, citations: Citation[]) {
    const msg = messages.value.find(m => m.id === msgId)
    if (msg) {
      msg.citations = citations
      msg.streaming = false
    }
    streaming.value = false
  }

  return {
    conversations,
    currentConversation,
    messages,
    loading,
    streaming,
    fetchConversations,
    fetchMessages,
    createConversation,
    createApplicationConversation,
    deleteConversation,
    selectConversation,
    addUserMessage,
    startAssistantMessage,
    appendToken,
    appendToolCall,
    finishAssistantMessage,
  }
})
