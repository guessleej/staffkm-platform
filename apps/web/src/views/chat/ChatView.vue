<template>
  <div class="flex h-full">
    <!-- 對話清單側欄 -->
    <div class="w-64 border-r border-gray-200 bg-white flex flex-col">
      <div class="p-4 border-b border-gray-200">
        <h2 class="font-semibold text-gray-800 mb-3">智慧問答</h2>
        <button @click="showNewChat = true"
          class="w-full flex items-center justify-center gap-2 bg-indigo-600 text-white text-sm py-2 rounded-lg hover:bg-indigo-700 transition">
          <span>＋</span> 新增對話
        </button>
      </div>
      <div class="flex-1 overflow-y-auto p-2 space-y-1">
        <button
          v-for="conv in conversations"
          :key="conv.id"
          @click="selectConversation(conv.id)"
          class="w-full text-left px-3 py-2.5 rounded-lg text-sm transition group"
          :class="activeConvId === conv.id ? 'bg-indigo-50 text-indigo-700' : 'text-gray-700 hover:bg-gray-100'"
        >
          <div class="flex items-center justify-between">
            <p class="font-medium truncate flex-1">{{ conv.title }}</p>
            <span class="opacity-0 group-hover:opacity-100 flex items-center gap-0.5 ml-1 flex-shrink-0">
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
            </span>
          </div>
          <p class="text-xs text-gray-400 mt-0.5">{{ conv.scenario_id }} · {{ conv.message_count }} 則訊息</p>
        </button>
        <p v-if="!conversations.length" class="text-center text-xs text-gray-400 py-6">尚無對話記錄</p>
      </div>
    </div>

    <!-- 對話主區域 -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- 無選擇狀態 -->
      <div v-if="!activeConvId" class="flex-1 flex items-center justify-center">
        <div class="text-center">
          <p class="text-xs uppercase tracking-widest text-neutral-400 mb-2">尚未選取對話</p>
          <h3 class="text-lg font-semibold text-gray-700 mb-2">選擇或新增對話</h3>
          <p class="text-sm text-gray-400">從左側選取對話，或點選「新增對話」開始諮詢</p>
        </div>
      </div>

      <!-- 對話畫面 -->
      <template v-else>
        <div class="h-14 border-b border-gray-200 px-6 flex items-center justify-between bg-white">
          <h3 class="font-semibold text-gray-800">{{ activeConv?.title }}</h3>
          <button @click="deleteConversation" class="text-xs text-red-500 hover:underline">刪除對話</button>
        </div>

        <!-- 訊息列表 -->
        <div ref="messagesEl" class="flex-1 overflow-y-auto p-6 space-y-6">
          <div v-for="msg in messages" :key="msg.id"
            class="flex" :class="msg.role === 'user' ? 'justify-end' : 'justify-start'">
            <div class="max-w-xl">
              <div class="px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap"
                :class="msg.role === 'user'
                  ? 'bg-indigo-600 text-white rounded-br-sm'
                  : 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm shadow-sm'">
                {{ msg.content }}
              </div>
              <!-- 引用來源 -->
              <div v-if="msg.citations?.length" class="mt-2 space-y-1">
                <p class="text-xs text-gray-400">參考來源：</p>
                <div v-for="(c, i) in msg.citations" :key="i"
                  class="text-xs bg-amber-50 border border-amber-200 rounded px-2 py-1 text-amber-800">
                  {{ c.doc_name }}（相符度 {{ (c.score * 100).toFixed(1) }}%）
                </div>
              </div>
            </div>
          </div>

          <!-- 串流中的 AI 回應 -->
          <div v-if="streamingText" class="flex justify-start">
            <div class="max-w-xl bg-white border border-gray-200 rounded-2xl rounded-bl-sm shadow-sm px-4 py-3 text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">
              {{ streamingText }}<span class="animate-pulse">▌</span>
            </div>
          </div>
        </div>

        <!-- 輸入區 -->
        <div class="p-4 border-t border-gray-200 bg-white">
          <div class="flex gap-3 items-end">
            <textarea
              v-model="inputText"
              @keydown.enter.exact.prevent="sendMessage"
              placeholder="輸入問題，按 Enter 傳送（Shift+Enter 換行）"
              rows="1"
              class="flex-1 resize-none border border-gray-300 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition max-h-36"
            />
            <button
              @click="sendMessage"
              :disabled="sending || !inputText.trim()"
              class="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-xl px-4 py-3 text-sm font-medium transition"
            >
              {{ sending ? '…' : '傳送' }}
            </button>
          </div>
        </div>
      </template>
    </div>
  </div>

  <!-- 新增對話 Modal -->
  <Teleport to="body">
    <div v-if="showNewChat" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="showNewChat = false">
      <div class="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-md">
        <h3 class="font-bold text-gray-900 mb-4">選擇諮詢類型</h3>
        <div class="grid grid-cols-2 gap-3 mb-4">
          <button
            v-for="agent in agents"
            :key="agent.scenario_id"
            @click="createConversation(agent.scenario_id)"
            class="p-4 rounded-xl border-2 border-gray-200 hover:border-indigo-400 hover:bg-indigo-50 text-left transition"
          >
            <p class="font-medium text-gray-800 text-sm">{{ agent.name }}</p>
            <p class="text-xs text-gray-400 mt-1 line-clamp-2">{{ agent.description }}</p>
          </button>
        </div>
        <button @click="showNewChat = false" class="w-full text-sm text-gray-500 hover:underline">取消</button>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue'
import { chatApi, streamChat } from '../../api/chat'
import { http } from '../../api/index'

const conversations = ref<any[]>([])
const activeConvId = ref<string | null>(null)
const messages = ref<any[]>([])
const agents = ref<any[]>([])
const inputText = ref('')
const sending = ref(false)
const streamingText = ref('')
const showNewChat = ref(false)
const messagesEl = ref<HTMLElement | null>(null)

const activeConv = computed(() => conversations.value.find(c => c.id === activeConvId.value))

async function loadConversations() {
  const data = await chatApi.listConversations()
  conversations.value = data.data || []
}

async function loadAgents() {
  const { data } = await http.get('/agents')
  agents.value = data.data || []
}

async function selectConversation(id: string) {
  activeConvId.value = id
  messages.value = await chatApi.getMessages(id)
  await nextTick()
  scrollToBottom()
}

async function createConversation(scenarioId: string) {
  showNewChat.value = false
  const conv = await chatApi.createConversation(scenarioId)
  await loadConversations()
  await selectConversation(conv.conversation_id)
}

async function deleteConversation() {
  if (!activeConvId.value) return
  await chatApi.deleteConversation(activeConvId.value)
  activeConvId.value = null
  messages.value = []
  await loadConversations()
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

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || !activeConvId.value || sending.value) return

  inputText.value = ''
  sending.value = true
  streamingText.value = ''
  messages.value.push({ id: Date.now(), role: 'user', content: text, citations: [] })
  await nextTick()
  scrollToBottom()

  await streamChat(
    activeConvId.value,
    text,
    (token) => { streamingText.value += token; scrollToBottom() },
    (citations) => {
      messages.value.push({ id: Date.now() + 1, role: 'assistant', content: streamingText.value, citations })
      streamingText.value = ''
    },
    async () => {
      sending.value = false
      await loadConversations()
      scrollToBottom()
    },
    (err) => { sending.value = false; console.error(err) },
  )
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  })
}

onMounted(() => { loadConversations(); loadAgents() })
</script>
