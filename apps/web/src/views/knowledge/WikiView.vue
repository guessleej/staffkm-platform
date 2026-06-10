<template>
  <div class="flex flex-col h-full overflow-hidden bg-surface-base">
    <!-- Header -->
    <div class="bg-surface-raised border-b border-neutral-200 px-6 py-3 flex items-center justify-between flex-shrink-0">
      <div class="flex items-center gap-3">
        <button
          class="p-1.5 rounded-lg text-neutral-400 hover:text-fg hover:bg-neutral-100 transition-colors"
          title="返回知識庫"
          @click="router.push('/knowledge')"
        >
          <span class="text-base">←</span>
        </button>
        <div>
          <h1 class="heading-section text-fg flex items-center gap-2">
            <SIcon name="book-open" :size="18" class="text-brand-600" />
            LLM Wiki
          </h1>
          <p class="text-[11px] text-fg-secondary font-mono">{{ kbId }}</p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <span v-if="statusText" class="text-xs" :class="statusClass">{{ statusText }}</span>
        <button
          :disabled="generating || isRunning"
          class="inline-flex items-center gap-1.5 h-9 px-4 text-sm font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-lg disabled:opacity-50 transition-colors"
          @click="generate"
        >
          <SIcon name="zap" :size="15" />
          {{ pages.length ? '重新生成' : '生成 Wiki' }}
        </button>
      </div>
    </div>

    <!-- 教學卡（首次/空狀態時最有用，但永遠保留入口）-->
    <div v-if="!pages.length && !isRunning" class="flex-1 overflow-auto px-6 py-10">
      <div class="max-w-2xl mx-auto text-center space-y-5">
        <div class="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-brand-50 text-brand-600">
          <SIcon name="book-open" :size="28" />
        </div>
        <h2 class="text-lg font-semibold text-fg">把這個知識庫整理成一本可瀏覽的百科</h2>
        <p class="text-sm text-fg-secondary leading-relaxed">
          按「生成 Wiki」後，系統會用<strong class="text-fg">地端 LLM</strong>逐份閱讀此知識庫的文件，
          整理成一頁頁結構化的 Wiki（標題、總覽、章節、關鍵事實），再生成一頁「總覽」串起所有主題。<br />
          完成後就能像翻百科一樣<strong class="text-fg">瀏覽</strong>，而不只是逐題問答。
        </p>
        <div class="text-xs text-fg-tertiary bg-neutral-50 border border-neutral-200 rounded-lg px-4 py-3 text-left space-y-1.5">
          <p>• 內容<strong class="text-fg-secondary">忠於原文</strong>，由 LLM 重新整理段落、不杜撰；最多整理 {{ maxDocs }} 份文件。</p>
          <p>• 生成在<strong class="text-fg-secondary">背景</strong>進行（每份文件一次 LLM 呼叫），文件多時需數分鐘，可離開稍後再回來。</p>
          <p>• 文件更新後，重新生成即可刷新整本 Wiki。</p>
        </div>
        <p v-if="errorText" class="text-sm text-danger-600">{{ errorText }}</p>
      </div>
    </div>

    <!-- 生成中 -->
    <div v-else-if="isRunning && !pages.length" class="flex-1 flex items-center justify-center">
      <div class="text-center space-y-3">
        <div class="w-8 h-8 mx-auto border-2 border-brand-200 border-t-brand-600 rounded-full animate-spin"></div>
        <p class="text-sm text-fg-secondary">正在生成 Wiki… {{ progressText }}</p>
        <p class="text-xs text-fg-tertiary">背景進行中，可離開稍後再回來查看</p>
      </div>
    </div>

    <!-- Wiki 主體：左 TOC + 右內容 -->
    <div v-else class="flex-1 flex min-h-0">
      <!-- TOC -->
      <aside class="w-64 flex-shrink-0 border-r border-neutral-200 bg-surface-raised overflow-auto py-3">
        <p class="px-4 pb-2 text-[11px] font-semibold text-fg-tertiary uppercase tracking-wide">目錄</p>
        <button
          v-for="p in pages"
          :key="p.id"
          class="w-full text-left px-4 py-2 text-sm transition-colors flex items-center gap-2"
          :class="currentId === p.id
            ? 'bg-brand-50 text-brand-700 font-medium border-l-2 border-brand-500'
            : 'text-fg-secondary hover:bg-neutral-100 border-l-2 border-transparent'"
          @click="selectPage(p.id)"
        >
          <SIcon :name="p.is_index ? 'bookmark' : 'file-text'" :size="14" class="flex-shrink-0 opacity-70" />
          <span class="truncate">{{ p.title }}</span>
        </button>
        <p v-if="isRunning" class="px-4 pt-3 text-xs text-fg-tertiary flex items-center gap-1.5">
          <span class="w-3 h-3 border border-brand-300 border-t-brand-600 rounded-full animate-spin"></span>
          仍在生成… {{ progressText }}
        </p>
      </aside>

      <!-- 內容 -->
      <main class="flex-1 overflow-auto">
        <div class="max-w-3xl mx-auto px-8 py-8">
          <div v-if="pageLoading" class="text-sm text-fg-secondary">載入中…</div>
          <article
            v-else-if="currentContent"
            class="wiki-md text-fg"
            v-html="renderedContent"
          ></article>
          <p v-else class="text-sm text-fg-secondary">選擇左側目錄中的一頁開始閱讀。</p>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { SIcon } from '@staffkm/ui-kit'
import { knowledgeApi } from '../../api/knowledge'
import { renderMarkdown } from '../../utils/markdown'

const route = useRoute()
const router = useRouter()
const kbId = route.params.kbId as string

const maxDocs = 50
const status = ref<any>({ status: 'none' })
const pages = ref<Array<{ id: string; title: string; document_id: string | null; is_index: boolean }>>([])
const currentId = ref<string | null>(null)
const currentContent = ref('')
const pageLoading = ref(false)
const generating = ref(false)
const errorText = ref('')
let pollTimer: number | undefined

const isRunning = computed(() => ['running', 'queued'].includes(status.value?.status))
const progressText = computed(() => {
  const s = status.value
  return s?.total ? `（${s.done || 0}/${s.total}）` : ''
})
const statusText = computed(() => {
  const s = status.value?.status
  if (s === 'running' || s === 'queued') return `生成中 ${progressText.value}`
  if (s === 'done') return `共 ${pages.value.length} 頁`
  if (s === 'error') return '生成失敗'
  return ''
})
const statusClass = computed(() =>
  status.value?.status === 'error' ? 'text-danger-600' : 'text-fg-tertiary')
const renderedContent = computed(() => renderMarkdown(currentContent.value))

async function load() {
  try {
    const data = await knowledgeApi.getWiki(kbId)
    status.value = data.status || { status: 'none' }
    pages.value = data.pages || []
    if (status.value?.status === 'error') errorText.value = status.value?.error || '生成失敗'
    // 預設打開第一頁（總覽）
    if (pages.value.length && !currentId.value) {
      await selectPage(pages.value[0].id)
    }
  } catch (e: any) {
    errorText.value = e?.response?.data?.message || '載入 Wiki 失敗'
  }
}

async function selectPage(id: string) {
  currentId.value = id
  pageLoading.value = true
  try {
    const data = await knowledgeApi.getWikiPage(kbId, id)
    currentContent.value = data.content || ''
  } catch {
    currentContent.value = '_載入此頁失敗_'
  } finally {
    pageLoading.value = false
  }
}

async function generate() {
  generating.value = true
  errorText.value = ''
  try {
    await knowledgeApi.generateWiki(kbId)
    status.value = { status: 'queued' }
    startPolling()
  } catch (e: any) {
    errorText.value = e?.response?.data?.message || '無法開始生成'
  } finally {
    generating.value = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = window.setInterval(async () => {
    await load()
    if (!isRunning.value) stopPolling()
  }, 4000)
}
function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = undefined }
}

onMounted(async () => {
  await load()
  if (isRunning.value) startPolling()
})
onUnmounted(stopPolling)
</script>

<style scoped>
.wiki-md :deep(h1) { font-size: 1.5rem; font-weight: 700; margin: 0.2em 0 0.6em; line-height: 1.3; }
.wiki-md :deep(h2) { font-size: 1.2rem; font-weight: 600; margin: 1.4em 0 0.5em; padding-bottom: 0.25em; border-bottom: 1px solid hsl(var(--color-border-default)); }
.wiki-md :deep(h3) { font-size: 1.05rem; font-weight: 600; margin: 1.1em 0 0.4em; }
.wiki-md :deep(p) { margin: 0.6em 0; line-height: 1.75; font-size: 0.92rem; }
.wiki-md :deep(ul), .wiki-md :deep(ol) { margin: 0.6em 0; padding-left: 1.4em; line-height: 1.75; font-size: 0.92rem; }
.wiki-md :deep(li) { margin: 0.25em 0; }
.wiki-md :deep(li)::marker { color: hsl(var(--color-brand-500)); }
.wiki-md :deep(strong) { font-weight: 600; color: hsl(var(--color-brand-700)); }
.wiki-md :deep(code) { background: hsl(var(--color-neutral-100)); padding: 0.1em 0.35em; border-radius: 4px; font-size: 0.85em; }
.wiki-md :deep(pre) { background: hsl(var(--color-neutral-100)); padding: 0.8em 1em; border-radius: 8px; overflow-x: auto; margin: 0.8em 0; }
.wiki-md :deep(pre code) { background: none; padding: 0; }
.wiki-md :deep(table) { border-collapse: collapse; margin: 0.8em 0; font-size: 0.88rem; width: 100%; }
.wiki-md :deep(th), .wiki-md :deep(td) { border: 1px solid hsl(var(--color-border-default)); padding: 0.4em 0.7em; text-align: left; }
.wiki-md :deep(th) { background: hsl(var(--color-neutral-100)); font-weight: 600; }
.wiki-md :deep(blockquote) { border-left: 3px solid hsl(var(--color-brand-300)); padding-left: 1em; margin: 0.8em 0; color: hsl(var(--color-text-secondary)); }
.wiki-md :deep(a) { color: hsl(var(--color-brand-600)); text-decoration: underline; }
.wiki-md :deep(hr) { border: none; border-top: 1px solid hsl(var(--color-border-default)); margin: 1.4em 0; }
</style>
