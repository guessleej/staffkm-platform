import { defineStore } from 'pinia'
import { ref } from 'vue'
import { http } from '../api/index'

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  citations: Citation[]
  created_at: string
  streaming?: boolean
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
  scenario_id: string
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
    const conv = data.data
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
    deleteConversation,
    selectConversation,
    addUserMessage,
    startAssistantMessage,
    appendToken,
    finishAssistantMessage,
  }
})
