<template>
  <div class="flex flex-col h-screen bg-surface-sunken">
    <!-- Header -->
    <div class="bg-surface-raised border-b px-6 py-4 flex items-center gap-3 shadow-sm">
      <div class="w-10 h-10 rounded-xl flex items-center justify-center text-xl" :style="{ background: gradient }">
        {{ app?.icon || 'AI' }}
      </div>
      <div>
        <h1 class="font-semibold text-fg">{{ app?.name || '載入中…' }}</h1>
        <p class="text-xs text-fg-tertiary">{{ app?.description }}</p>
      </div>
      <div class="ml-auto">
        <span class="text-xs text-fg-tertiary bg-surface-sunken px-3 py-1 rounded-full border">Powered by StaffKM</span>
      </div>
    </div>

    <!-- 歡迎畫面 -->
    <div v-if="messages.length === 0" class="flex-1 flex flex-col items-center justify-center px-6 text-center">
      <div class="w-20 h-20 rounded-2xl flex items-center justify-center text-4xl mb-6" :style="{ background: gradient }">
        {{ app?.icon || 'AI' }}
      </div>
      <h2 class="text-xl font-semibold text-fg mb-2">{{ app?.welcome_message || '你好！有什麼我可以幫助你的？' }}</h2>
      <p class="text-sm text-fg-tertiary mb-8">{{ app?.description }}</p>
      <div class="flex flex-col gap-2 w-full max-w-md">
        <button
          v-for="q in app?.suggested_questions"
          :key="q"
          @click="sendMessage(q)"
          class="text-left px-4 py-3 bg-surface-raised rounded-xl border text-sm text-fg-secondary hover:border-indigo-300 hover:bg-indigo-50/50 transition-all"
        >
          {{ q }}
        </button>
      </div>
    </div>

    <!-- 訊息列表 -->
    <div v-else ref="msgContainer" class="flex-1 overflow-y-auto px-4 py-6 space-y-4 max-w-3xl mx-auto w-full">
      <div
        v-for="msg in messages"
        :key="msg.id"
        class="flex"
        :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
      >
        <div v-if="msg.role === 'assistant'" class="max-w-[85%] flex items-start gap-3">
          <div class="w-8 h-8 rounded-lg flex items-center justify-center text-sm flex-shrink-0" :style="{ background: gradient }">
            {{ app?.icon || 'AI' }}
          </div>
          <div class="bg-surface-raised border rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
            <p class="text-sm text-fg whitespace-pre-wrap">{{ msg.content }}</p>
            <div v-if="msg.streaming" class="flex gap-1 mt-2">
              <span class="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style="animation-delay:0ms"/>
              <span class="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style="animation-delay:150ms"/>
              <span class="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style="animation-delay:300ms"/>
            </div>
          </div>
        </div>
        <div v-else class="max-w-[75%] bg-indigo-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm">
          <p class="text-sm whitespace-pre-wrap">{{ msg.content }}</p>
        </div>
      </div>
    </div>

    <!-- 輸入框 -->
    <div class="bg-surface-raised border-t px-4 py-3">
      <div class="flex gap-3 items-end max-w-3xl mx-auto">
        <textarea
          v-model="input"
          @keydown.enter.exact.prevent="() => sendMessage()"
          rows="1"
          placeholder="輸入問題…（Enter 送出）"
          :disabled="streaming"
          class="flex-1 resize-none rounded-xl border px-4 py-2.5 text-sm focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition"
        />
        <button
          @click="() => sendMessage()"
          :disabled="!input.trim() || streaming"
          class="h-10 w-10 flex-shrink-0 flex items-center justify-center rounded-xl bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-40 transition"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"/>
          </svg>
        </button>
      </div>
      <p class="text-center text-xs text-fg-tertiary mt-2">AI 可能產生錯誤，重要資訊請查閱官方文件</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const appId = route.params.appId as string

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  streaming?: boolean
}

const app = ref<any>(null)
const messages = ref<Message[]>([])
const input = ref('')
const streaming = ref(false)
const msgContainer = ref<HTMLElement | null>(null)

const gradient = `linear-gradient(135deg, hsl(${parseInt(appId.slice(-4), 16) % 360},70%,88%), hsl(${(parseInt(appId.slice(-4), 16) + 40) % 360},70%,88%))`

onMounted(async () => {
  const resp = await fetch(`/api/v1/public/applications/${appId}`)
  if (resp.ok) {
    const data = await resp.json()
    app.value = data.data
  }
})

function scrollBottom() {
  nextTick(() => {
    if (msgContainer.value) {
      msgContainer.value.scrollTop = msgContainer.value.scrollHeight
    }
  })
}

async function sendMessage(text?: string) {
  const content = (text ?? input.value).trim()
  if (!content || streaming.value) return
  input.value = ''

  messages.value.push({ id: crypto.randomUUID(), role: 'user', content })
  const aMsg: Message = { id: crypto.randomUUID(), role: 'assistant', content: '', streaming: true }
  messages.value.push(aMsg)
  streaming.value = true
  scrollBottom()

  try {
    const response = await fetch(`/api/v1/public/applications/${appId}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify({
        messages: messages.value
          .filter(m => !m.streaming)
          .map(m => ({ role: m.role, content: m.content })),
      }),
    })

    if (!response.ok || !response.body) throw new Error('SSE 連線失敗')

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
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
          if (pendingEvent === 'token') {
            const msg = messages.value.find(m => m.id === aMsg.id)
            if (msg) {
              msg.content += line.slice(6)
              scrollBottom()
            }
          }
          pendingEvent = ''
        }
      }
    }
  } catch {
    const msg = messages.value.find(m => m.id === aMsg.id)
    if (msg && !msg.content) msg.content = '錯誤：回應時發生錯誤，請稍後再試。'
  }

  const msg = messages.value.find(m => m.id === aMsg.id)
  if (msg) msg.streaming = false
  streaming.value = false
}
</script>
