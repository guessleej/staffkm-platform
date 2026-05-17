<template>
  <div class="h-full flex flex-col">
    <!-- ───────── 空狀態：置中歡迎 + 輸入區 ───────── -->
    <div
      v-if="!activeConv && !streamingText"
      class="flex-1 flex flex-col items-center justify-center px-6 py-12 max-w-3xl mx-auto w-full"
    >
      <div class="text-center mb-10">
        <h1 class="text-2xl font-semibold text-neutral-900 mb-2">
          {{ $t('chat.welcome') }}
        </h1>
        <p class="text-sm text-neutral-500">{{ $t('chat.welcomeHint') }}</p>
        <!-- Sprint 19.x：Project scope binding 指示 -->
        <div v-if="projectStore.active" class="mt-3 inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-brand-50 text-brand-700 text-xs">
          <span>{{ projectStore.active.emoji || '#' }}</span>
          <span>使用 Project：<strong>{{ projectStore.active.name }}</strong></span>
          <span class="text-brand-500">·</span>
          <span>{{ projectStore.active.knowledge_base_ids.length }} 個 KB 自動加入 RAG</span>
        </div>
      </div>

      <ChatInput
        v-model="draft"
        :disabled="sending"
        :placeholder="$t('chat.inputPlaceholder')"
        class="w-full"
        @submit="onSubmit"
      />

      <!-- 建議的快速起始 -->
      <div v-if="agents.length" class="mt-6 flex flex-wrap gap-2 justify-center">
        <button
          v-for="a in agents.slice(0, 4)"
          :key="a.scenario_id"
          @click="startWithScenario(a.scenario_id)"
          class="px-3 py-1.5 text-xs rounded-full border border-neutral-200 text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900 transition"
        >{{ a.name }}</button>
      </div>
    </div>

    <!-- ───────── 對話進行中 ───────── -->
    <template v-else>
      <!-- 訊息流（可滾動） -->
      <div ref="messagesEl" class="flex-1 overflow-y-auto">
        <div class="max-w-3xl mx-auto w-full px-6 py-8 space-y-6">
          <article
            v-for="msg in convStore.messages"
            :key="msg.id"
            class="text-[15px] leading-7 group"
          >
            <!-- 訊息 meta -->
            <header class="mb-1 text-[11px] uppercase tracking-widest text-neutral-400 flex items-center justify-between">
              <span>{{ msg.role === 'user' ? '你' : 'staffKM' }}</span>
              <!-- 助理回應 + 長度足夠 → 顯示「在右側展開」-->
              <button
                v-if="msg.role === 'assistant' && shouldOfferArtifact(msg.content)"
                @click="openMessageAsArtifact(msg)"
                class="opacity-0 group-hover:opacity-100 transition flex items-center gap-1 text-fg-tertiary hover:text-brand-600 normal-case tracking-normal"
                title="在右側展開為可滾動 / 複製的 markdown 預覽"
              >
                <SIcon name="external-link" :size="12" />
                <span class="text-[10px]">展開</span>
              </button>
            </header>
            <!-- 訊息內容（無頭像 chip，純文字段落） -->
            <div
              class="whitespace-pre-wrap"
              :class="msg.role === 'user' ? 'text-neutral-900' : 'text-neutral-800'"
            >{{ msg.content }}</div>
            <!-- 引用來源（點開展開 ArtifactPane）-->
            <ul
              v-if="msg.citations?.length"
              class="mt-2 space-y-1 text-xs text-neutral-500"
            >
              <li
                v-for="(c, i) in msg.citations"
                :key="i"
                class="border-l-2 border-neutral-200 pl-2 cursor-pointer hover:text-neutral-900 hover:border-neutral-400 transition"
                @click="openCitation(c)"
              >{{ c.doc_name }} · 相符度 {{ (c.score * 100).toFixed(0) }}%</li>
            </ul>
          </article>

          <!-- 串流中的回應 -->
          <article v-if="streamingText" class="text-[15px] leading-7">
            <header class="mb-1 text-[11px] uppercase tracking-widest text-neutral-400">
              staffKM
            </header>
            <div class="whitespace-pre-wrap text-neutral-800">
              {{ streamingText }}<span class="animate-pulse">▌</span>
            </div>
          </article>
        </div>
      </div>

      <!-- 底部 sticky 輸入區 -->
      <div class="border-t border-neutral-100 bg-surface-base">
        <div class="max-w-3xl mx-auto w-full px-6 py-4">
          <ChatInput
            v-model="draft"
            :disabled="sending"
            :placeholder="$t('chat.continuePlaceholder')"
            @submit="onSubmit"
          />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import ChatInput from '../../components/chat/ChatInput.vue'
import { useConversationStore } from '../../stores/conversation'
import { useArtifactStore } from '../../stores/artifact'
import { useProjectStore } from '../../stores/project'
import { http } from '../../api'
import { streamChat } from '../../api/chat'
import { SIcon } from '@staffkm/ui-kit'

const route = useRoute()
const convStore = useConversationStore()
const projectStore = useProjectStore()
const artifact = useArtifactStore()

function openCitation(c: { doc_name: string; content: string }) {
  artifact.open({
    kind: 'document',
    title: c.doc_name || '引用來源',
    content: c.content || '（無內容）',
  })
}

// 18-B：長訊息 / 含 code block 的助理回應 → 提供「右側展開」
function shouldOfferArtifact(content: string): boolean {
  if (!content) return false
  return content.length >= 600 || /```|^\s*#{1,6}\s|^\s*[-*]\s|\|.*\|/m.test(content)
}
function openMessageAsArtifact(msg: { content: string; created_at?: string }) {
  const tsRaw = msg.created_at ? new Date(msg.created_at) : new Date()
  const ts = isNaN(tsRaw.getTime()) ? new Date() : tsRaw
  artifact.open({
    kind: 'document',
    title: `助理回應 · ${ts.toLocaleTimeString('zh-TW', { hour12: false })}`,
    content: msg.content,
  })
}

const draft = ref('')
const sending = ref(false)
const streamingText = ref('')
const messagesEl = ref<HTMLElement | null>(null)
const agents = ref<{ scenario_id: string; name: string }[]>([])

const activeConv = computed(() => convStore.currentConversation)

async function loadAgents() {
  try {
    const { data } = await http.get('/agents')
    agents.value = (data.data || []).map((a: any) => ({
      scenario_id: a.scenario_id,
      name: a.name,
    }))
  } catch { /* 非關鍵 */ }
}

async function selectFromRoute() {
  const id = route.query.conv as string
  if (!id) { convStore.currentConversation = null; convStore.messages = []; return }
  const conv = convStore.conversations.find((c) => c.id === id)
  if (conv) {
    convStore.selectConversation(conv)
    await convStore.fetchMessages(id)
    nextTick(scrollToBottom)
  }
}

async function startWithScenario(scenarioId: string) {
  // Sprint 19.x：active Project → 自動把 project 的 KB list 帶進新對話 RAG scope
  const projectKbs = projectStore.active?.knowledge_base_ids ?? []
  const title = projectStore.active
    ? `[${projectStore.active.emoji || '#'} ${projectStore.active.name}] 新對話`
    : undefined
  const conv = await convStore.createConversation(scenarioId, title, projectKbs)
  if (conv) convStore.selectConversation(conv as any)
  history.replaceState(null, '', `?conv=${(conv as any)?.id || ''}`)
}

async function onSubmit() {
  const text = draft.value.trim()
  if (!text || sending.value) return
  // 若無 active conv，先用預設 scenario 開一個
  if (!activeConv.value) {
    const first = agents.value[0]?.scenario_id
    if (!first) return
    await startWithScenario(first)
  }
  sending.value = true
  streamingText.value = ''
  convStore.addUserMessage(text)
  draft.value = ''
  nextTick(scrollToBottom)

  // 在送出前先建好 assistant 訊息容器（用於累積 token + citations）
  const assistant = convStore.startAssistantMessage()
  try {
    await streamChat(
      activeConv.value!.id,
      text,
      (token) => {
        streamingText.value += token
        convStore.appendToken(assistant.id, token)
        scrollToBottom()
      },
      (citations) => {
        convStore.finishAssistantMessage(assistant.id, citations as any[])
      },
      () => {
        streamingText.value = ''
        sending.value = false
        nextTick(scrollToBottom)
      },
      () => {
        sending.value = false
        streamingText.value = ''
      },
    )
  } catch {
    sending.value = false
    streamingText.value = ''
  }
}

function scrollToBottom() {
  const el = messagesEl.value
  if (el) el.scrollTop = el.scrollHeight
}

watch(() => route.query.conv, selectFromRoute, { immediate: false })

onMounted(async () => {
  await loadAgents()
  await selectFromRoute()
})
</script>
