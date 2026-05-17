<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0"
      leave-active-class="transition duration-150 ease-in"
      leave-to-class="opacity-0"
    >
      <div
        v-if="modelValue"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-900/50 backdrop-blur-sm"
        @click.self="close"
      >
        <div class="w-full max-w-2xl h-[80vh] bg-surface-raised rounded-2xl shadow-2xl flex flex-col overflow-hidden">
          <!-- 頭 -->
          <header class="px-5 py-4 border-b border-neutral-100 flex items-center gap-3 flex-shrink-0">
            <div class="w-10 h-10 rounded-xl bg-brand-50 flex items-center justify-center text-xl flex-shrink-0">
              {{ template?.emoji || '🎮' }}
            </div>
            <div class="min-w-0 flex-1">
              <h3 class="font-semibold text-sm text-fg truncate">試試「{{ template?.name }}」</h3>
              <p class="text-[11px] text-fg-tertiary mt-0.5">preview 模式 · 不會建立應用、不計 usage</p>
            </div>
            <button @click="close" class="p-1.5 rounded-md text-fg-tertiary hover:text-fg hover:bg-neutral-100">
              <SIcon name="x" :size="18" />
            </button>
          </header>

          <!-- 訊息流 -->
          <div ref="msgsEl" class="flex-1 overflow-y-auto px-5 py-4 space-y-4">
            <article
              v-for="(m, i) in messages" :key="i"
              class="text-[14px] leading-7"
            >
              <header class="mb-1 text-[10px] uppercase tracking-widest text-fg-tertiary">
                {{ m.role === 'user' ? '你' : 'staffKM' }}
              </header>
              <div
                class="whitespace-pre-wrap"
                :class="m.role === 'user' ? 'text-fg' : 'text-fg-secondary'"
              >{{ m.content }}</div>
            </article>

            <!-- 串流中 -->
            <article v-if="streaming" class="text-[14px] leading-7">
              <header class="mb-1 text-[10px] uppercase tracking-widest text-fg-tertiary">staffKM</header>
              <div class="whitespace-pre-wrap text-fg-secondary">
                {{ streamBuffer }}<span class="animate-pulse">▌</span>
              </div>
            </article>

            <!-- 建議快速起始（剩下還沒問過的） -->
            <div v-if="!sending && template?.suggested_questions?.length && messages.length <= 1"
                 class="flex flex-wrap gap-2 pt-2">
              <button
                v-for="(q, i) in template.suggested_questions" :key="i"
                @click="send(q)"
                class="px-3 py-1.5 text-xs rounded-full border border-neutral-200 text-fg-secondary hover:bg-brand-50 hover:border-brand-300 hover:text-brand-700 transition"
              >{{ q }}</button>
            </div>
          </div>

          <!-- 輸入 -->
          <div class="border-t border-neutral-100 px-5 py-3 bg-neutral-50/40 flex-shrink-0">
            <div class="flex gap-2">
              <input
                v-model="draft"
                @keydown.enter.prevent="send(draft)"
                :disabled="sending"
                placeholder="輸入訊息試試看..."
                class="flex-1 h-10 px-3 text-sm rounded-lg border border-neutral-200 focus:border-brand-500 focus:ring-2 focus:ring-brand-100 outline-none disabled:opacity-50"
              />
              <button
                @click="send(draft)"
                :disabled="sending || !draft.trim()"
                class="h-10 px-4 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 disabled:opacity-50"
              >送出</button>
            </div>
            <div class="flex items-center justify-between mt-3">
              <p class="text-[11px] text-fg-tertiary">
                💡 滿意嗎？可以正式建立應用 →
              </p>
              <button
                @click="$emit('create-from-template'); close()"
                class="px-3 py-1.5 text-xs font-medium text-brand-700 bg-brand-50 hover:bg-brand-100 rounded-md transition"
              >建立此應用</button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { SIcon } from '@staffkm/ui-kit'
import { streamPreviewChat } from '../../api/chat'
import type { AppTemplate } from '../../data/appTemplates'

const props = defineProps<{
  modelValue: boolean
  template: AppTemplate | null
}>()
const emit = defineEmits<{
  'update:modelValue': [v: boolean]
  'create-from-template': []
}>()

interface Msg { role: 'user' | 'assistant'; content: string }
const messages = ref<Msg[]>([])
const draft = ref('')
const sending = ref(false)
const streaming = ref(false)
const streamBuffer = ref('')
const msgsEl = ref<HTMLElement | null>(null)

function close() { emit('update:modelValue', false) }

// 開啟時 reset + 顯示 welcome
watch(() => props.modelValue, (open) => {
  if (open && props.template) {
    messages.value = props.template.welcome_message
      ? [{ role: 'assistant', content: props.template.welcome_message }]
      : []
    draft.value = ''
    streamBuffer.value = ''
    sending.value = false
    streaming.value = false
  }
})

async function send(text: string) {
  const content = text.trim()
  if (!content || sending.value || !props.template) return
  draft.value = ''
  messages.value.push({ role: 'user', content })
  await nextTick(scrollBottom)

  sending.value = true
  streaming.value = true
  streamBuffer.value = ''

  // welcome message 不算對話歷史（preview 本意是「假對話」），只送真實 user/assistant
  const apiMsgs = messages.value.filter((m, i) => !(i === 0 && m.role === 'assistant' && props.template?.welcome_message === m.content))

  try {
    await streamPreviewChat(
      {
        messages: apiMsgs,
        system_prompt: props.template.system_prompt,
        welcome_message: props.template.welcome_message,
      },
      (tok) => { streamBuffer.value += tok; scrollBottom() },
      () => {
        if (streamBuffer.value) {
          messages.value.push({ role: 'assistant', content: streamBuffer.value })
        }
        streaming.value = false
        sending.value = false
        streamBuffer.value = ''
        nextTick(scrollBottom)
      },
      (err) => {
        messages.value.push({ role: 'assistant', content: `（preview 失敗：${err}）` })
        streaming.value = false
        sending.value = false
        streamBuffer.value = ''
      },
    )
  } catch (e: any) {
    streaming.value = false
    sending.value = false
    messages.value.push({ role: 'assistant', content: `（preview 例外：${e?.message || e}）` })
  }
}

function scrollBottom() {
  const el = msgsEl.value
  if (el) el.scrollTop = el.scrollHeight
}
</script>
