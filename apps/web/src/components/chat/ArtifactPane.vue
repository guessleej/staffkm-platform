<template>
  <transition
    enter-active-class="transition-transform duration-300 ease-out"
    enter-from-class="translate-x-full"
    leave-active-class="transition-transform duration-200 ease-in"
    leave-to-class="translate-x-full"
  >
    <aside
      v-if="store.isOpen && a"
      class="w-[520px] flex flex-col bg-surface-raised border-l border-neutral-200 flex-shrink-0 overflow-hidden"
    >
      <!-- 標題列 -->
      <header class="h-12 px-4 flex items-center justify-between border-b border-neutral-100 flex-shrink-0">
        <div class="flex items-center gap-2 min-w-0">
          <span class="text-[10px] uppercase tracking-widest text-fg-tertiary flex-shrink-0 font-mono">
            {{ kindLabel }}
          </span>
          <span class="text-sm font-medium text-fg truncate">{{ a.title }}</span>
        </div>
        <div class="flex items-center gap-1 flex-shrink-0">
          <button
            v-if="canCopy"
            @click="onCopy"
            class="w-8 h-8 flex items-center justify-center rounded-lg text-fg-tertiary hover:bg-neutral-100 hover:text-fg transition"
            :title="copied ? '已複製' : '複製內容'"
          >
            <SIcon :name="copied ? 'check' : 'copy'" :size="14" />
          </button>
          <button
            @click="store.close()"
            class="w-8 h-8 flex items-center justify-center rounded-lg text-fg-tertiary hover:bg-neutral-100 hover:text-fg transition"
            title="關閉（Esc）"
          >
            <SIcon name="x" :size="16" />
          </button>
        </div>
      </header>

      <!-- 內容區 -->
      <div class="flex-1 overflow-y-auto">
        <!-- document：markdown rendered -->
        <article
          v-if="a.kind === 'document'"
          class="px-5 py-4 text-[14px] leading-7 text-fg-secondary artifact-markdown"
          v-html="renderedMd"
        />

        <!-- code：highlight.js -->
        <pre
          v-else-if="a.kind === 'code'"
          class="px-5 py-4 text-[13px] leading-6 font-mono bg-neutral-50 overflow-x-auto m-0"
        ><code class="hljs" :class="`language-${a.language || 'text'}`" v-html="renderedCode" /></pre>

        <!-- image -->
        <div v-else-if="a.kind === 'image'" class="p-4 flex items-center justify-center">
          <img :src="a.src" :alt="a.alt || a.title" class="max-w-full max-h-[80vh] rounded-md" />
        </div>

        <!-- iframe -->
        <iframe
          v-else-if="a.kind === 'iframe'"
          :src="a.src"
          class="w-full h-full border-0"
          sandbox="allow-scripts allow-same-origin"
        />

        <!-- workflow 摘要 -->
        <div v-else-if="a.kind === 'workflow'" class="px-5 py-4 text-sm text-fg-secondary">
          <p class="text-fg-tertiary mb-3">Workflow 預覽（待接 LogicFlow mini renderer）</p>
          <ul class="space-y-1 text-xs font-mono">
            <li v-for="n in a.nodes" :key="n.id">
              {{ n.node_type }} · {{ n.node_key }}
            </li>
          </ul>
          <p class="mt-3 text-xs text-fg-tertiary">
            {{ a.nodes.length }} 節點 · {{ a.edges.length }} 連線
          </p>
        </div>
      </div>
    </aside>
  </transition>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { renderMarkdown } from '../../utils/markdown'
// 19-perf：highlight.js/lib/common 只含 top ~30 個常用 language
// （vs 預設 192 個 → md-vendor 從 1MB 縮到 ~250KB）
import hljs from 'highlight.js/lib/common'
import 'highlight.js/styles/github.css'

import { SIcon } from '@staffkm/ui-kit'
import { useArtifactStore } from '../../stores/artifact'

const store = useArtifactStore()
const a = computed(() => store.current)

const kindLabel = computed(() => {
  switch (a.value?.kind) {
    case 'document': return 'DOC'
    case 'code':     return 'CODE'
    case 'image':    return 'IMG'
    case 'workflow': return 'FLOW'
    case 'iframe':   return 'WEB'
    default:         return ''
  }
})

const canCopy = computed(() => {
  const kind = a.value?.kind
  return kind === 'document' || kind === 'code'
})

const copied = ref(false)
async function onCopy() {
  const cur = a.value
  if (!cur) return
  const text = (cur.kind === 'document' || cur.kind === 'code') ? cur.content : ''
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    copied.value = true
    setTimeout(() => { copied.value = false }, 1500)
  } catch { /* clipboard 被瀏覽器禁時不致命 */ }
}

// v5.12: markdown 走集中消毒 util（DOMPurify）。
// 原註解「安全模式（不解析 raw HTML）」是誤解 — marked 預設**會**解析 raw HTML，需 sanitize。
const renderedMd = computed(() => {
  const cur = a.value
  if (!cur || cur.kind !== 'document') return ''
  return renderMarkdown(cur.content || '')
})

// code 高亮（highlight.js auto-detect 或指定 language）
const renderedCode = computed(() => {
  const cur = a.value
  if (!cur || cur.kind !== 'code') return ''
  const lang = cur.language
  try {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(cur.content, { language: lang, ignoreIllegals: true }).value
    }
    return hljs.highlightAuto(cur.content).value
  } catch {
    return cur.content
  }
})

// ESC 關閉
function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape' && store.isOpen) store.close()
}
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<style scoped>
/* markdown 內部樣式：scoped 以 :deep() 穿透 v-html */
.artifact-markdown :deep(h1) { @apply text-xl font-bold mt-4 mb-2 text-fg; }
.artifact-markdown :deep(h2) { @apply text-lg font-semibold mt-3 mb-2 text-fg; }
.artifact-markdown :deep(h3) { @apply text-base font-semibold mt-2.5 mb-1.5 text-fg; }
.artifact-markdown :deep(p)  { @apply mb-3; }
.artifact-markdown :deep(ul), .artifact-markdown :deep(ol) { @apply pl-5 mb-3 space-y-1; }
.artifact-markdown :deep(ul) { @apply list-disc; }
.artifact-markdown :deep(ol) { @apply list-decimal; }
.artifact-markdown :deep(a)  { @apply text-brand-600 underline hover:text-brand-700; }
.artifact-markdown :deep(code) { @apply bg-neutral-100 text-brand-700 px-1 py-0.5 rounded text-[13px] font-mono; }
.artifact-markdown :deep(pre) { @apply bg-neutral-50 rounded-lg p-3 my-3 overflow-x-auto; }
.artifact-markdown :deep(pre code) { @apply bg-transparent text-fg p-0; }
.artifact-markdown :deep(blockquote) { @apply border-l-4 border-neutral-200 pl-4 italic text-fg-secondary my-3; }
.artifact-markdown :deep(table) { @apply w-full text-sm my-3 border border-neutral-200 rounded-lg overflow-hidden; }
.artifact-markdown :deep(th), .artifact-markdown :deep(td) { @apply px-3 py-1.5 border-b border-neutral-100; }
.artifact-markdown :deep(th) { @apply bg-neutral-50 font-semibold text-fg text-left; }
.artifact-markdown :deep(hr) { @apply my-4 border-neutral-200; }
</style>
