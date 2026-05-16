<template>
  <div class="flex h-full overflow-hidden">
    <!-- 左側：對話列表 -->
    <div class="w-64 bg-white border-r border-gray-200 flex flex-col flex-shrink-0">
      <div class="p-3 border-b border-gray-100">
        <button @click="newConversation" class="w-full flex items-center justify-center gap-2 py-2 px-3 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
          </svg>
          新對話
        </button>
      </div>

      <div class="flex-1 overflow-y-auto p-2 space-y-0.5">
        <button
          v-for="conv in convStore.conversations"
          :key="conv.id"
          @click="selectConv(conv)"
          class="w-full text-left px-3 py-2.5 rounded-lg text-sm transition group"
          :class="convStore.currentConversation?.id === conv.id ? 'bg-indigo-50 text-indigo-700' : 'text-gray-700 hover:bg-gray-100'"
        >
          <div class="flex items-center justify-between">
            <span class="truncate flex-1">{{ conv.title || '未命名對話' }}</span>
            <span class="opacity-0 group-hover:opacity-100 flex items-center gap-0.5 ml-1">
              <button
                @click.stop="exportConversation(conv.id, 'markdown')"
                class="text-gray-300 hover:text-indigo-500 transition text-[10px] font-mono leading-none px-0.5"
                title="匯出 Markdown"
              >.md</button>
              <button
                @click.stop="exportConversation(conv.id, 'json')"
                class="text-gray-300 hover:text-indigo-500 transition text-[10px] font-mono leading-none px-0.5"
                title="匯出 JSON"
              >.json</button>
              <button
                @click.stop="deleteConv(conv.id)"
                class="text-gray-300 hover:text-rose-400 transition text-lg leading-none ml-0.5"
              >×</button>
            </span>
          </div>
          <p class="text-[11px] text-gray-400 mt-0.5">{{ conv.message_count }} 則訊息</p>
        </button>
      </div>

      <!-- 返回應用列表 -->
      <div class="p-3 border-t border-gray-100">
        <router-link to="/applications" class="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-700 transition">
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
          </svg>
          返回應用列表
        </router-link>
      </div>
    </div>

    <!-- 右側：對話主區 -->
    <div class="flex-1 flex flex-col overflow-hidden bg-gray-50">
      <!-- 頁首 -->
      <div class="bg-white border-b border-gray-200 px-5 py-3 flex items-center gap-3 flex-shrink-0">
        <div class="w-8 h-8 rounded-lg flex items-center justify-center text-lg flex-shrink-0"
             :style="{ background: appGradient(appId) }">
          {{ application?.icon || appEmoji(application?.name || '') }}
        </div>
        <div>
          <h2 class="text-sm font-semibold text-gray-900">{{ application?.name || '載入中…' }}</h2>
          <p class="text-xs text-gray-400">{{ application?.description }}</p>
        </div>
      </div>

      <!-- 歡迎畫面（無選中對話） -->
      <div v-if="!convStore.currentConversation" class="flex-1 flex flex-col items-center justify-center px-6 text-center">
        <div class="w-16 h-16 rounded-2xl flex items-center justify-center text-3xl mb-5"
             :style="{ background: appGradient(appId) }">
          {{ application?.icon || appEmoji(application?.name || '') }}
        </div>
        <h3 class="text-lg font-semibold text-gray-900 mb-2">{{ application?.welcome_message || '開始對話' }}</h3>
        <p class="text-sm text-gray-500 mb-6 max-w-md">{{ application?.description }}</p>

        <!-- 建議問題 -->
        <div v-if="application?.suggested_questions?.length" class="flex flex-col gap-2 w-full max-w-md">
          <p class="text-xs text-gray-400 mb-1">試試以下問題：</p>
          <button
            v-for="q in application.suggested_questions"
            :key="q"
            @click="sendSuggestedQuestion(q)"
            class="text-left px-4 py-3 bg-white rounded-xl border border-gray-200 text-sm text-gray-700 hover:border-indigo-300 hover:bg-indigo-50/50 transition-all"
          >
            {{ q }}
          </button>
        </div>

        <button @click="newConversation" class="mt-6 px-5 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-700 transition">
          開始新對話
        </button>
      </div>

      <!-- 訊息列表 -->
      <div v-else ref="msgContainer" class="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        <div
          v-for="msg in convStore.messages"
          :key="msg.id"
          class="flex"
          :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
        >
          <!-- AI 訊息 -->
          <div v-if="msg.role === 'assistant'" class="max-w-[85%] flex items-start gap-3">
            <div class="w-7 h-7 rounded-lg flex items-center justify-center text-sm flex-shrink-0 mt-0.5"
                 :style="{ background: appGradient(appId) }">
              {{ application?.icon || 'AI' }}
            </div>
            <div>
              <div class="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
                <p class="text-sm text-gray-800 whitespace-pre-wrap">{{ msg.content }}</p>
                <div v-if="msg.streaming" class="flex gap-1 mt-2">
                  <span class="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style="animation-delay:0ms"/>
                  <span class="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style="animation-delay:150ms"/>
                  <span class="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style="animation-delay:300ms"/>
                </div>
              </div>
              <!-- 引用來源 -->
              <div v-if="msg.citations?.length" class="mt-2 flex flex-wrap gap-1.5">
                <span
                  v-for="(c, i) in msg.citations.slice(0,3)"
                  :key="i"
                  class="px-2 py-0.5 bg-indigo-50 text-indigo-600 text-[10px] rounded-full border border-indigo-100"
                  :title="c.content"
                >
                  {{ i + 1 }}. {{ c.doc_name }}
                </span>
              </div>
            </div>
          </div>

          <!-- 使用者訊息 -->
          <div v-else-if="msg.role === 'user'" class="max-w-[75%]">
            <div class="bg-indigo-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm">
              <p class="text-sm whitespace-pre-wrap">{{ msg.content }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 輸入框 -->
      <div v-if="convStore.currentConversation" class="bg-white border-t border-gray-200 px-4 py-3 flex-shrink-0">
        <div class="flex gap-3 items-end max-w-4xl mx-auto">
          <textarea
            v-model="input"
            @keydown.enter.exact.prevent="sendMessage"
            @keydown.enter.shift.exact="input += '\n'"
            rows="1"
            class="flex-1 resize-none rounded-xl border border-gray-200 px-4 py-2.5 text-sm focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition"
            :style="{ maxHeight: '120px', overflowY: 'auto' }"
            placeholder="輸入問題（Enter 送出，Shift+Enter 換行）"
            :disabled="convStore.streaming"
          />
          <button
            @click="sendMessage"
            :disabled="!input.trim() || convStore.streaming"
            class="h-10 w-10 flex-shrink-0 flex items-center justify-center rounded-xl bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"/>
            </svg>
          </button>
        </div>
        <p class="text-center text-[11px] text-gray-300 mt-2">AI 可能產生錯誤，重要資訊請查閱官方文件</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useConversationStore } from '../../stores/conversation'
import { applicationApi, type Application } from '../../api/application'

const route = useRoute()
const convStore = useConversationStore()
const appId = route.params.appId as string

const application = ref<Application | null>(null)
const input = ref('')
const msgContainer = ref<HTMLElement | null>(null)

async function load() {
  const { data } = await applicationApi.get(appId)
  application.value = data.data
  await convStore.fetchConversations(appId)
}

async function newConversation() {
  await convStore.createConversation(appId, '新對話')
}

async function selectConv(conv: any) {
  convStore.selectConversation(conv)
  await convStore.fetchMessages(conv.id)
  scrollBottom()
}

async function deleteConv(id: string) {
  await convStore.deleteConversation(id)
}

function exportConversation(convId: string, format: 'markdown' | 'json') {
  const token = localStorage.getItem('access_token')
  const ext = format === 'json' ? 'json' : 'md'
  fetch(`/api/v1/chat/conversations/${convId}/export?format=${format}`, {
    headers: { Authorization: `Bearer ${token}` }
  })
    .then(r => r.blob())
    .then(blob => {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `conversation-${convId.slice(0, 8)}.${ext}`
      a.click()
      URL.revokeObjectURL(url)
    })
}

async function sendSuggestedQuestion(q: string) {
  await newConversation()
  input.value = q
  await sendMessage()
}

async function sendMessage() {
  const text = input.value.trim()
  if (!text || convStore.streaming) return
  input.value = ''

  convStore.addUserMessage(text)
  const assistantMsg = convStore.startAssistantMessage()
  convStore.streaming = true
  scrollBottom()

  try {
    const response = await fetch(`/api/v1/applications/${appId}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        Accept: 'text/event-stream',
      },
      body: JSON.stringify({
        session_id: convStore.currentConversation?.id ?? convStore.currentConversation?.conversation_id,
        messages: convStore.messages
          .filter(m => !m.streaming)
          .map(m => ({ role: m.role, content: m.content })),
        kb_ids: application.value?.knowledge_base_ids ?? [],
      }),
    })

    if (!response.ok || !response.body) throw new Error('SSE 連線失敗')

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let citations: any[] = []
    let pendingEvent = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          pendingEvent = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (pendingEvent === 'token') {
            convStore.appendToken(assistantMsg.id, data)
            scrollBottom()
          } else if (pendingEvent === 'citations') {
            try { citations = JSON.parse(data) } catch { /* ignore */ }
          } else if (pendingEvent === 'error') {
            convStore.appendToken(assistantMsg.id, `\n\n錯誤：${data}`)
          }
          // reset after data line consumed
          pendingEvent = ''
        } else if (line === '') {
          pendingEvent = ''
        }
      }
    }

    convStore.finishAssistantMessage(assistantMsg.id, citations)
  } catch (e) {
    convStore.finishAssistantMessage(assistantMsg.id, [])
    convStore.appendToken(assistantMsg.id, '\n\n錯誤：回應時發生錯誤，請稍後再試。')
  }
}

function scrollBottom() {
  nextTick(() => {
    if (msgContainer.value) {
      msgContainer.value.scrollTop = msgContainer.value.scrollHeight
    }
  })
}

function appGradient(id: string) {
  const hue = parseInt((id ?? '').slice(-4), 16) % 360
  return `linear-gradient(135deg, hsl(${hue},70%,88%), hsl(${(hue + 40) % 360},70%,88%))`
}
function appEmoji(name: string) {
  const map: Record<string, string> = { 'sop': 'SOP', '請假': '假', '採購': '購', '財務': '財', '人事': '人', '公文': '文', '法規': '法', '知識': '知' }
  for (const [k, v] of Object.entries(map)) {
    if (name.includes(k)) return v
  }
  return 'AI'
}

onMounted(load)
</script>
