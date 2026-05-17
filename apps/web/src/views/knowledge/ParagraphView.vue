<template>
  <div class="flex flex-col h-full bg-surface-base">
    <!-- 頂部 -->
    <div class="px-6 py-4 border-b border-neutral-200 bg-surface-raised flex items-center justify-between flex-shrink-0">
      <div class="flex items-center gap-3 min-w-0">
        <button
          @click="$router.back()"
          class="p-1.5 rounded-lg text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700"
          aria-label="返回"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
          </svg>
        </button>
        <div class="min-w-0">
          <h1 class="text-base font-semibold text-neutral-900 truncate">{{ docName || '段落' }}</h1>
          <p class="text-xs text-neutral-500 mt-0.5">共 {{ paragraphs.length }} 段 · 拖曳可重新排序</p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <button @click="onGenerateAll" :disabled="generating"
                class="h-8 px-3 text-xs text-neutral-600 bg-surface-raised border border-neutral-200 rounded-lg hover:border-brand-400 hover:text-brand-600 disabled:opacity-50">
          {{ generating ? '生成中…' : '為文件產生 Q&A' }}
        </button>
        <button @click="refresh"
                class="h-8 px-3 text-xs text-neutral-600 bg-surface-raised border border-neutral-200 rounded-lg hover:border-brand-400 hover:text-brand-600">
          重新整理
        </button>
      </div>
    </div>

    <!-- 段落列表 -->
    <div class="flex-1 overflow-y-auto p-6 space-y-3">
      <p v-if="loading" class="text-sm text-neutral-400 text-center py-12">載入中…</p>
      <p v-else-if="!paragraphs.length" class="text-sm text-neutral-400 text-center py-12">
        此文件尚無段落。請等待向量化完成或檢查處理狀態。
      </p>
      <div
        v-for="(p, idx) in paragraphs"
        :key="p.id"
        :class="['group relative border rounded-xl p-4 transition bg-surface-raised',
                 dragOverIdx === idx ? 'border-brand-400 ring-2 ring-brand-100' : 'border-neutral-200 hover:border-neutral-300',
                 draggingIdx === idx ? 'opacity-40' : '']"
        draggable="true"
        @dragstart="onDragStart(idx, $event)"
        @dragover.prevent="onDragOver(idx)"
        @dragleave="dragOverIdx = -1"
        @drop="onDrop(idx)"
        @dragend="onDragEnd"
      >
        <!-- 拖曳手把 -->
        <div class="absolute -left-3 top-1/2 -translate-y-1/2 hidden group-hover:flex items-center justify-center w-6 h-10 rounded text-neutral-300 cursor-grab active:cursor-grabbing"
             title="拖曳排序">
          <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 16 16">
            <circle cx="6" cy="3" r="1.2"/><circle cx="10" cy="3" r="1.2"/>
            <circle cx="6" cy="8" r="1.2"/><circle cx="10" cy="8" r="1.2"/>
            <circle cx="6" cy="13" r="1.2"/><circle cx="10" cy="13" r="1.2"/>
          </svg>
        </div>
        <!-- 段落內容 -->
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <span class="text-[11px] text-neutral-400 font-mono">#{{ idx + 1 }}</span>
              <span v-if="p.title" class="text-[12px] font-medium text-neutral-700">{{ p.title }}</span>
              <span v-if="(p.qa_pairs?.length || 0) > 0"
                    class="text-[10px] px-1.5 py-0.5 bg-brand-50 text-brand-700 rounded">
                {{ p.qa_pairs.length }} 個 Q&A
              </span>
            </div>
            <p class="text-sm text-neutral-800 whitespace-pre-wrap line-clamp-6">{{ p.content }}</p>
          </div>
          <div class="flex flex-col gap-1 flex-shrink-0">
            <button @click="moveBtn(p.id, 'up')" :disabled="idx === 0"
                    class="p-1 text-neutral-400 hover:text-brand-600 hover:bg-brand-50 rounded disabled:opacity-30 disabled:cursor-not-allowed"
                    title="上移">▲</button>
            <button @click="moveBtn(p.id, 'down')" :disabled="idx === paragraphs.length - 1"
                    class="p-1 text-neutral-400 hover:text-brand-600 hover:bg-brand-50 rounded disabled:opacity-30 disabled:cursor-not-allowed"
                    title="下移">▼</button>
            <button @click="moveBtn(p.id, 'top')" :disabled="idx === 0"
                    class="p-1 text-neutral-400 hover:text-brand-600 hover:bg-brand-50 rounded disabled:opacity-30 text-xs"
                    title="移到頂">⇈</button>
            <button @click="moveBtn(p.id, 'bottom')" :disabled="idx === paragraphs.length - 1"
                    class="p-1 text-neutral-400 hover:text-brand-600 hover:bg-brand-50 rounded disabled:opacity-30 text-xs"
                    title="移到底">⇊</button>
            <button @click="generateOne(p.id)" :disabled="busyQA === p.id"
                    class="p-1 text-neutral-400 hover:text-brand-600 hover:bg-brand-50 rounded disabled:opacity-50 text-[10px]"
                    title="為此段產生 Q&A">Q&A</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 儲存提示 -->
    <transition
      enter-active-class="transition duration-200" enter-from-class="opacity-0 translate-y-2"
      leave-active-class="transition duration-150" leave-to-class="opacity-0 translate-y-2">
      <div v-if="saving"
           class="fixed bottom-6 left-1/2 -translate-x-1/2 z-30 bg-neutral-900 text-white text-xs px-4 py-2 rounded-lg shadow-lg">
        正在儲存排序…
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { knowledgeApi } from '../../api/knowledge'

const route = useRoute()
const docId = route.params.docId as string

const paragraphs = ref<any[]>([])
const loading = ref(true)
const generating = ref(false)
const saving = ref(false)
const busyQA = ref<string | null>(null)
const docName = ref('')

async function refresh() {
  loading.value = true
  try {
    const { data } = await (await import('../../api/index')).http.get(`/knowledge/paragraphs/${docId}`)
    paragraphs.value = data?.data || []
    // 額外撈文件名稱（best-effort）
    try {
      const docResp = await knowledgeApi.getDocQuestions(docId)
      // docResp 是 questions[]；名稱只能從段落 title 推測，或留空
      void docResp
    } catch { /* skip */ }
  } catch (e: any) {
    alert('讀取段落失敗：' + (e?.response?.data?.detail || e?.message))
  } finally {
    loading.value = false
  }
}

// ── 拖拽 ──────────────────────────────────────────────────────────
const draggingIdx = ref(-1)
const dragOverIdx = ref(-1)

function onDragStart(idx: number, e: DragEvent) {
  draggingIdx.value = idx
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(idx))
  }
}

function onDragOver(idx: number) {
  dragOverIdx.value = idx
}

async function onDrop(targetIdx: number) {
  const fromIdx = draggingIdx.value
  dragOverIdx.value = -1
  if (fromIdx < 0 || fromIdx === targetIdx) return

  // optimistic：先在本地重排
  const arr = paragraphs.value.slice()
  const [moved] = arr.splice(fromIdx, 1)
  arr.splice(targetIdx, 0, moved)
  paragraphs.value = arr

  // 寫回
  saving.value = true
  try {
    await knowledgeApi.reorderParagraphs(docId, arr.map((p: any) => p.id))
  } catch (e: any) {
    alert('排序儲存失敗：' + (e?.response?.data?.detail || e?.message))
    await refresh()
  } finally {
    saving.value = false
  }
}

function onDragEnd() {
  draggingIdx.value = -1
  dragOverIdx.value = -1
}

// ── 上下移動按鈕 ──────────────────────────────────────────────────
async function moveBtn(pid: string, direction: 'up' | 'down' | 'top' | 'bottom') {
  saving.value = true
  try {
    await knowledgeApi.moveParagraph(pid, direction)
    await refresh()
  } catch (e: any) {
    alert('移動失敗：' + (e?.response?.data?.detail || e?.message))
  } finally {
    saving.value = false
  }
}

// ── Q&A 生成 ──────────────────────────────────────────────────────
async function generateOne(pid: string) {
  busyQA.value = pid
  try {
    const r = await knowledgeApi.generateParagraphQA(pid, { n: 3 })
    const idx = paragraphs.value.findIndex((p: any) => p.id === pid)
    if (idx >= 0) paragraphs.value[idx] = { ...paragraphs.value[idx], qa_pairs: r?.qa_pairs || [] }
  } catch (e: any) {
    alert('Q&A 生成失敗：' + (e?.response?.data?.detail || e?.message))
  } finally {
    busyQA.value = null
  }
}

async function onGenerateAll() {
  if (!confirm('對所有段落跑 Q&A 生成？會呼叫 LLM 多次，可能需要 1~2 分鐘。')) return
  generating.value = true
  try {
    const r = await knowledgeApi.generateDocQuestions(docId, { per_paragraph: 2, max_paragraphs: 50 })
    alert(`已處理 ${r?.processed ?? 0} 段；共 ${r?.questions?.length ?? 0} 個常見問題`)
    await refresh()
  } catch (e: any) {
    alert('生成失敗：' + (e?.response?.data?.detail || e?.message))
  } finally {
    generating.value = false
  }
}

onMounted(refresh)
</script>
