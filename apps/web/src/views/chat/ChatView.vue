<template>
  <div class="h-full flex flex-col">
    <!-- ───────── 空狀態：置中歡迎 + 輸入區（v5.1 Warm Enterprise）───────── -->
    <div
      v-if="!activeConv && !streamingText"
      class="flex-1 flex flex-col items-center justify-center px-6 py-12 max-w-3xl mx-auto w-full view-stagger"
    >
      <div class="text-center mb-10 stagger-item-1">
        <h1 class="text-3xl font-semibold tracking-tight text-fg mb-2">
          今天想了解什麼？
        </h1>
        <p class="text-sm text-fg-tertiary">{{ $t('chat.welcomeHint') }}</p>
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
        class="w-full stagger-item-2"
        @submit="onSubmit"
      />

      <!-- v5.1：starter prompt 卡片（2x2 grid） -->
      <div v-if="starterPrompts.length" class="mt-8 w-full grid grid-cols-1 sm:grid-cols-2 gap-3 stagger-item-3">
        <button
          v-for="(p, i) in starterPrompts"
          :key="p.title"
          @click="useStarter(p)"
          class="card-warm fade-up text-left p-4 flex items-start gap-3 group cursor-pointer"
          :style="{ animationDelay: (i * 60) + 'ms' }"
        >
          <div
            class="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 transition-transform group-hover:scale-110"
            :style="{ background: p.bg, color: p.color }"
          >
            <SIcon :name="p.icon" :size="18" :stroke-width="1.8" />
          </div>
          <div class="min-w-0">
            <div class="text-sm font-semibold text-fg">{{ p.title }}</div>
            <div class="text-xs text-fg-tertiary mt-0.5 line-clamp-2">{{ p.prompt }}</div>
          </div>
        </button>
      </div>

      <!-- 既有 agents pills 仍保留為次選（如有） -->
      <div v-if="agents.length" class="mt-6 flex flex-wrap gap-2 justify-center">
        <button
          v-for="a in agents.slice(0, 4)"
          :key="a.scenario_id"
          @click="startWithScenario(a.scenario_id)"
          class="px-3 py-1.5 text-xs rounded-full border border-bd text-fg-secondary hover:bg-surface-soft hover:text-fg transition"
        >{{ a.name }}</button>
      </div>
    </div>

    <!-- ───────── 對話進行中 ───────── -->
    <template v-else>
      <!-- v2.7：對話頂部 actions（分享 / 匯出可在此擴充） -->
      <div class="px-6 pt-3 pb-1 flex items-center justify-end gap-2 flex-shrink-0">
        <button
          @click="onShare"
          class="inline-flex items-center gap-1 px-2.5 h-7 text-[12px] text-neutral-500 hover:text-brand-700 hover:bg-brand-50 rounded-md transition"
          title="產生公開分享連結（唯讀）"
        >
          <SIcon name="share-2" :size="12" />
          分享
        </button>
      </div>

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
            <!-- 訊息內容：user 純文字、assistant 渲染 markdown (v5.9.31) -->
            <template v-if="msg.role === 'assistant'">
              <MarkdownMessage
                v-if="msg.content"
                :content="msg.content"
                class="text-neutral-800"
              />
              <!-- v5.10.15：提交後到首 token 前的「思考中」閃爍 → 讓使用者知道還活著；
                   無法回答時 streaming 會被關閉 → 不閃（見 onError / catch） -->
              <div
                v-else-if="msg.streaming"
                class="flex items-center gap-2 py-1 text-neutral-400"
                aria-label="思考中"
              >
                <span class="inline-flex gap-1 items-center">
                  <span class="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse"></span>
                  <span class="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse [animation-delay:200ms]"></span>
                  <span class="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse [animation-delay:400ms]"></span>
                </span>
                <span class="text-xs animate-pulse">思考中…</span>
              </div>
            </template>
            <div
              v-else
              class="whitespace-pre-wrap text-neutral-900"
            >{{ msg.content }}</div>
            <!-- v2.7：tool_calls 折疊顯示（MaxKB UI 對齊） -->
            <ToolCallBlock
              v-if="msg.role === 'assistant' && msg.tool_calls?.length"
              :calls="msg.tool_calls"
              class="mt-2"
            />
            <!-- v2.3-B / v5.11.21：引用來源 — inline chip。移除會蓋住主區的 hover 預覽框；
                 滑過用原生 title 顯示片段（瀏覽器定位、不蓋版面），點擊開 ArtifactPane 看完整內容。 -->
            <div v-if="msg.citations?.length" class="mt-3 flex flex-wrap gap-1.5">
              <button
                v-for="(c, i) in msg.citations"
                :key="i"
                @click="openCitation(c)"
                :title="(c.doc_name ? c.doc_name + '\n\n' : '') + (c.content || '').slice(0, 300) + ((c.content || '').length > 300 ? '…（點擊看完整）' : '')"
                class="inline-flex items-center gap-1.5 px-2 py-1 text-[11px] rounded-full
                       bg-brand-50/60 text-brand-700 border border-brand-100
                       hover:bg-brand-50 hover:border-brand-300 transition cursor-pointer max-w-[280px]"
              >
                <span class="inline-flex items-center justify-center w-4 h-4 rounded-full bg-brand-600 text-white text-[9px] font-bold flex-shrink-0">
                  {{ i + 1 }}
                </span>
                <span class="truncate font-medium">{{ c.doc_name || '引用' }}</span>
                <span class="text-fg-tertiary flex-shrink-0">{{ (c.score * 100).toFixed(0) }}%</span>
              </button>
            </div>
          </article>

          <!-- v5.10.15：思考中指示已移到 assistant 訊息本身（streaming && !content），
               提交後到首 token 前閃爍、無法回答則停止 → 此處舊 placeholder 已不需要 -->

          <!-- v5.12：切走後再切回、但伺服器仍在生成上一則回答（背景 task 尚未存好）→ 輪詢中指示。
               答案存好後自動補上（_maybePollForReply）。 -->
          <div
            v-if="pendingReply"
            class="flex items-center gap-2 py-1 text-neutral-400"
            aria-label="回應生成中"
          >
            <span class="inline-flex gap-1 items-center">
              <span class="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse"></span>
              <span class="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse [animation-delay:200ms]"></span>
              <span class="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse [animation-delay:400ms]"></span>
            </span>
            <span class="text-xs animate-pulse">回應生成中…（完成後自動顯示）</span>
          </div>

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
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import ChatInput from '../../components/chat/ChatInput.vue'
import ToolCallBlock from '../../components/chat/ToolCallBlock.vue'
import MarkdownMessage from '../../components/chat/MarkdownMessage.vue'
import { useConversationStore } from '../../stores/conversation'
import { useArtifactStore } from '../../stores/artifact'
import { useProjectStore } from '../../stores/project'
import { useChatOverrideStore } from '../../stores/chatOverride'
import { http } from '../../api'
import { streamChat, shareApi } from '../../api/chat'
import { useToast } from '../../composables/useToast'
import { SIcon } from '@staffkm/ui-kit'

const route = useRoute()
const convStore = useConversationStore()
const projectStore = useProjectStore()
const artifact = useArtifactStore()
const chatOverride = useChatOverrideStore()
const toast = useToast()

// MaxKB v2.7：分享當前對話
async function onShare() {
  if (!activeConv.value) return
  try {
    const res = await shareApi.share(activeConv.value.id)
    const url = `${window.location.origin}/share/${res.share_token}`
    await navigator.clipboard.writeText(url)
    toast.success('分享連結已複製：' + url)
  } catch (e: any) {
    toast.error('分享失敗：' + (e?.message || e))
  }
}

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

// v5.1 — Welcome starter prompts（暖色 icon + 範例問題）
const starterPrompts = [
  {
    icon: 'search',
    title: '搜尋知識庫',
    prompt: '幫我找出最近三個月的請假規則更新',
    bg: 'hsl(38 92% 95%)',
    color: 'hsl(28 80% 40%)',
  },
  {
    icon: 'book-open',
    title: '彙整文件重點',
    prompt: '從我上傳的會議記錄中整理本季重要決議',
    bg: 'hsl(140 25% 94%)',
    color: 'hsl(140 35% 35%)',
  },
  {
    icon: 'edit',
    title: '草擬內部公告',
    prompt: '幫我寫一份新人到職第一週的指引信',
    bg: 'hsl(238 95% 96%)',
    color: 'hsl(239 72% 50%)',
  },
  {
    icon: 'info',
    title: 'FAQ 整理',
    prompt: '把員工常問的 IT 問題整理成 FAQ 條目',
    bg: 'hsl(210 85% 95%)',
    color: 'hsl(212 74% 40%)',
  },
] as Array<{ icon: string; title: string; prompt: string; bg: string; color: string }>

function useStarter(p: { prompt: string }) {
  draft.value = p.prompt
}
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

// v5.12：切走後再切回、但伺服器仍在生成上一則回答（後端背景 task 尚未存好）→ 輪詢補上。
//   後端已把生成+存檔與 client 連線解耦：答案最終會存進 DB；前端輪詢直到它出現。
const pendingReply = ref(false)
let _pollHandle: ReturnType<typeof setTimeout> | null = null

function stopReplyPoll() {
  if (_pollHandle) { clearTimeout(_pollHandle); _pollHandle = null }
  pendingReply.value = false
}

// 最後一則是「提問、後面沒有 assistant 回覆」→ 伺服器可能還在生成
function _lastIsUnansweredUser(): boolean {
  const msgs = convStore.messages
  return msgs.length > 0 && msgs[msgs.length - 1].role === 'user'
}

async function maybePollForReply(id: string) {
  stopReplyPoll()
  if (!_lastIsUnansweredUser()) return
  pendingReply.value = true
  const startedAt = Date.now()
  const tick = async () => {
    if (route.query.conv !== id) { stopReplyPoll(); return }   // 對話已切換
    if (Date.now() - startedAt > 90_000) { stopReplyPoll(); return }  // 逾時保險，不無限輪詢
    await convStore.fetchMessages(id)
    if (!_lastIsUnansweredUser()) { pendingReply.value = false; nextTick(scrollToBottom); return }  // 答案出現
    _pollHandle = setTimeout(tick, 2500)
  }
  _pollHandle = setTimeout(tick, 2500)
}

async function selectFromRoute() {
  stopReplyPoll()
  const id = route.query.conv as string
  // v5.13: 切到「不同」對話 → 關掉上一個對話的引用面板（避免幽靈殘留）。
  //   但 **不再清掉 KB/model 覆寫** —— 使用者選了知識庫應跨對話持續連動，否則一開新對話
  //   就回「預設」、查不到自己的 KB（v5.12 每次重置是此困擾的根源）。跨帳號的清除仍由
  //   ChatLayout onMounted 的 reset 處理，不影響安全。
  if (id !== convStore.currentConversation?.id) {
    artifact.close()
  }
  if (!id) { convStore.currentConversation = null; convStore.messages = []; return }
  // v5.12.x：返回到「正在串流中的同一對話」（例：聊天中點去設定看模型再點回來）→ **不** wipe+refetch。
  // 否則 selectConversation 清空 messages + fetchMessages 覆蓋會抹掉進行中的回答（背景 streamChat
  // 仍在跑、持續 append 到 store 的 assistant 訊息）→ 看起來像「點回來就沒在跑了」。保留即可續顯示。
  if (convStore.currentConversation?.id === id && convStore.messages.some((m) => m.streaming)) {
    nextTick(scrollToBottom)
    return
  }
  // v5.12：清單沒這筆（deep-link / reload / app 綁定的對話不在 scenario 清單）→ by-id 抓回，
  // 不再靜默空白。抓不到（404/403）→ 顯示空狀態。
  let conv = convStore.conversations.find((c) => c.id === id)
  if (!conv) conv = (await convStore.fetchConversationById(id)) ?? undefined
  if (conv) {
    convStore.selectConversation(conv)
    await convStore.fetchMessages(id)
    nextTick(scrollToBottom)
    await maybePollForReply(id)   // 若回答還沒存好（後端仍在生成）→ 輪詢補上
  } else {
    convStore.currentConversation = null
    convStore.messages = []
  }
}

onUnmounted(stopReplyPoll)

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

// v5.10.14：應用「開始問答」匯流進統一對話（取代獨立 ApplicationChatView）
async function startWithApplication(appId: string, appName?: string) {
  const projectKbs = projectStore.active?.knowledge_base_ids ?? []
  const title = appName ? `${appName}` : undefined
  const conv = await convStore.createApplicationConversation(appId, title, projectKbs)
  if (conv) convStore.selectConversation(conv as any)
  history.replaceState(null, '', `?conv=${(conv as any)?.id || ''}`)
}

async function onSubmit() {
  const text = draft.value.trim()
  if (!text || sending.value) return
  stopReplyPoll()   // 送新訊息 → 停掉等舊回答的輪詢，避免 fetchMessages 洗掉本地串流
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
      (e: string) => {
        // v5.12：顯示錯誤訊息而非留白 — LLM 失敗（如 host Ollama 沒起 → Connection error）時
        // 原本只關 streaming 留空泡泡，使用者零回饋。沒有任何 token 時補一則可見錯誤。
        if (!streamingText.value) {
          convStore.appendToken(assistant.id, `⚠️ 回應失敗：${e || '請稍後再試'}`)
        }
        convStore.finishAssistantMessage(assistant.id, [])
        sending.value = false
        streamingText.value = ''
      },
      {
        model_override:  chatOverride.model || null,
        kb_ids_override: chatOverride.kb_ids.length ? chatOverride.kb_ids : null,
      },
      // v5.10.14：應用對話的 function-calling 工具呼叫過程 → 折疊式 ToolCallBlock
      (tc) => {
        convStore.appendToolCall(assistant.id, {
          name: tc.name,
          status: tc.status === 'error' ? 'error' : 'success',
          input: (tc.input as Record<string, unknown>) ?? null,
          output: tc.output ?? null,
          error: tc.error ?? null,
        })
        scrollToBottom()
      },
    )
  } catch {
    // v5.10.15：例外也要關 streaming，否則思考中浮標會一直閃
    convStore.finishAssistantMessage(assistant.id, [])
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
  // v5.10.14：?app={id} 來自應用「開始問答」→ 自動建立應用對話（統一進對話）
  const appId = route.query.app as string
  if (appId) {
    await startWithApplication(appId, (route.query.appName as string) || undefined)
  } else {
    await selectFromRoute()
  }
})
</script>
