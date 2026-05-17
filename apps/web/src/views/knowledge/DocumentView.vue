<template>
  <div class="flex flex-col h-full overflow-hidden bg-surface-base">

    <!-- Header -->
    <div class="bg-surface-raised border-b border-neutral-200 px-6 py-3 flex items-center justify-between flex-shrink-0">
      <div class="flex items-center gap-3">
        <button
          @click="$router.push('/knowledge')"
          class="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 transition-colors"
          title="返回"
        >
          <IconArrowLeft :size="16" />
        </button>
        <div>
          <h2 class="text-base font-semibold text-neutral-900">文件</h2>
          <p class="text-[11px] text-neutral-400 font-mono">{{ kbId }}</p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <button
          @click="loadDocs"
          :disabled="loading"
          class="inline-flex items-center gap-1.5 h-8 px-3 text-xs text-neutral-600 bg-surface-raised border border-neutral-200 rounded-lg hover:border-brand-400 hover:text-brand-600 transition-colors disabled:opacity-50"
        >
          <IconRefresh :size="13" />
          重新整理
        </button>
        <button
          @click="onExportExcel"
          class="inline-flex items-center gap-1.5 h-8 px-3 text-xs text-neutral-600 bg-surface-raised border border-neutral-200 rounded-lg hover:border-brand-400 hover:text-brand-600 transition-colors"
          title="匯出全部文檔到 Excel"
        >匯出 Excel</button>
        <button
          @click="onExportZip"
          class="inline-flex items-center gap-1.5 h-8 px-3 text-xs text-neutral-600 bg-surface-raised border border-neutral-200 rounded-lg hover:border-brand-400 hover:text-brand-600 transition-colors"
          title="匯出全部文檔內容 ZIP"
        >匯出 ZIP</button>
        <button
          @click="($refs.fileInput as HTMLInputElement).click()"
          class="inline-flex items-center gap-1.5 h-8 px-3 text-xs font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-lg transition-colors"
        >
          <IconUpload :size="13" />
          上傳
        </button>
        <input
          ref="fileInput"
          type="file"
          class="hidden"
          accept=".pdf,.docx,.doc,.txt,.md,.xlsx,.csv"
          @change="onFileSelected"
        />
      </div>
    </div>

    <!-- Body -->
    <div
      class="flex-1 overflow-y-auto p-6"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="onDrop"
    >
      <!-- Drag overlay -->
      <div
        v-if="dragging"
        class="fixed inset-0 bg-brand-500/10 backdrop-blur-sm border-4 border-dashed border-brand-400 rounded-3xl flex items-center justify-center z-50 m-12 pointer-events-none"
      >
        <div class="flex flex-col items-center gap-3 text-brand-700">
          <IconUpload :size="32" />
          <p class="text-lg font-semibold">放開以上傳</p>
        </div>
      </div>

      <!-- Empty -->
      <div
        v-if="!loading && docs.length === 0"
        class="bg-surface-raised border-2 border-dashed border-neutral-200 rounded-2xl py-16 px-8 text-center"
      >
        <div class="w-16 h-16 mx-auto rounded-full bg-neutral-100 flex items-center justify-center text-neutral-400 mb-4">
          <IconFolder :size="28" :stroke-width="1.5" />
        </div>
        <p class="text-sm font-medium text-neutral-700 mb-1">尚未上傳文件</p>
        <p class="text-xs text-neutral-500 mb-5">支援 PDF、DOCX、TXT、MD、XLSX、CSV，單檔上限 50 MB</p>
        <button
          @click="($refs.fileInput as HTMLInputElement).click()"
          class="inline-flex items-center gap-1.5 h-9 px-4 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-lg transition-colors"
        >
          <IconUpload :size="14" />
          選擇檔案
        </button>
      </div>

      <!-- Loading -->
      <div v-else-if="loading && docs.length === 0" class="flex items-center justify-center py-16 text-neutral-400 text-sm gap-2">
        <IconSpinner :size="16" /> 載入中
      </div>

      <!-- Document table -->
      <div v-else class="bg-surface-raised rounded-2xl border border-neutral-200 overflow-hidden shadow-sm">
        <table class="w-full text-sm">
          <thead class="bg-neutral-50 border-b border-neutral-100">
            <tr class="text-left text-[11px] text-neutral-500 uppercase tracking-wider">
              <th class="px-3 py-3 font-semibold w-10">
                <input type="checkbox" class="w-3.5 h-3.5 accent-brand-600 cursor-pointer"
                       :checked="allSelected" :indeterminate.prop="someSelected"
                       @change="toggleAll" :aria-label="'全選 / 取消全選'" />
              </th>
              <th class="px-5 py-3 font-semibold">文件</th>
              <th class="px-5 py-3 font-semibold w-32">狀態</th>
              <th class="px-5 py-3 font-semibold w-48">處理進度</th>
              <th class="px-5 py-3 font-semibold w-20 text-right">段落</th>
              <th class="px-5 py-3 font-semibold w-24 text-right">大小</th>
              <th class="px-5 py-3 font-semibold w-12"></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="doc in docs"
              :key="doc.id"
              :class="['border-b border-neutral-50 last:border-0 transition-colors',
                       batch.isSelected(doc.id) ? 'bg-brand-50/40' : 'hover:bg-neutral-50/50']"
            >
              <td class="px-3 py-3">
                <input type="checkbox" class="w-3.5 h-3.5 accent-brand-600 cursor-pointer"
                       :checked="batch.isSelected(doc.id)"
                       @change="batch.toggle(doc.id)"
                       :aria-label="`選擇 ${doc.name}`" />
              </td>
              <td class="px-5 py-3">
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                       :class="fileTypeBg(doc.file_type)">
                    <component :is="fileTypeIcon(doc.file_type)" :size="14" />
                  </div>
                  <div class="min-w-0">
                    <div class="text-sm text-neutral-900 truncate max-w-[280px]" :title="doc.name">{{ doc.name }}</div>
                    <div class="text-[11px] text-neutral-400 font-mono uppercase">{{ doc.file_type }}</div>
                  </div>
                </div>
              </td>
              <td class="px-5 py-3">
                <span
                  class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium"
                  :class="statusChipClass(doc.status)"
                >
                  <span class="w-1.5 h-1.5 rounded-full" :class="statusDotClass(doc.status)"></span>
                  {{ statusLabel(doc.status) }}
                </span>
              </td>
              <td class="px-5 py-3">
                <div v-if="doc.status === 'processing' || doc.status === 'pending'" class="space-y-1">
                  <div class="h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                    <div
                      class="h-full bg-brand-500 transition-all duration-500"
                      :style="{ width: (doc.progress || 0) + '%' }"
                    />
                  </div>
                  <p class="text-[11px] text-neutral-500 truncate">{{ doc.progress_message || '等待中' }}</p>
                </div>
                <p
                  v-else-if="doc.status === 'error'"
                  class="text-[11px] text-danger-600 truncate flex items-center gap-1"
                  :title="doc.error_message"
                >
                  <IconWarning :size="12" />
                  {{ doc.error_message || '處理失敗' }}
                </p>
                <p v-else-if="doc.status === 'ready'" class="text-[11px] text-success-600 flex items-center gap-1">
                  <IconCheck :size="12" :stroke-width="2.5" />
                  完成
                </p>
              </td>
              <td class="px-5 py-3 text-sm text-neutral-600 text-right tabular-nums">
                {{ doc.paragraph_count || 0 }}
              </td>
              <td class="px-5 py-3 text-sm text-neutral-600 text-right tabular-nums">
                {{ formatSize(doc.file_size) }}
              </td>
              <td class="px-5 py-3">
                <div class="flex items-center gap-1">
                  <a :href="downloadUrl(doc)" download
                     class="text-neutral-400 hover:text-brand-600 transition-colors p-1.5 rounded-md"
                     title="下載原件">
                    <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/>
                    </svg>
                  </a>
                  <button @click="onGenerateQuestions(doc)"
                          class="text-neutral-400 hover:text-brand-600 transition-colors p-1.5 rounded-md"
                          title="生成問題">
                    <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/>
                    </svg>
                  </button>
                  <button @click="onDelete(doc)"
                          class="text-neutral-300 hover:text-danger-600 hover:bg-danger-50 transition-colors p-1.5 rounded-md"
                          title="刪除">
                    <IconDelete :size="14" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Upload toast -->
      <transition
        enter-active-class="transition-all duration-300 ease-out"
        enter-from-class="opacity-0 translate-y-2"
        enter-to-class="opacity-100 translate-y-0"
        leave-active-class="transition-all duration-200 ease-in"
        leave-to-class="opacity-0"
      >
        <div
          v-if="uploadingFile"
          class="fixed bottom-6 right-6 bg-surface-raised border border-neutral-200 rounded-2xl shadow-lg p-4 w-80 z-50"
        >
          <div class="flex items-center gap-3 mb-2">
            <div class="w-9 h-9 rounded-lg bg-brand-50 flex items-center justify-center text-brand-600 flex-shrink-0">
              <IconUpload :size="16" />
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-neutral-900 truncate">{{ uploadingFile.name }}</p>
              <p class="text-[11px] text-neutral-400">{{ uploadProgress }}% 上傳中</p>
            </div>
          </div>
          <div class="h-1.5 bg-neutral-100 rounded-full overflow-hidden">
            <div class="h-full bg-brand-500 transition-all" :style="{ width: uploadProgress + '%' }" />
          </div>
        </div>
      </transition>
    </div>

    <!-- v2.1 11-2：批量操作 toolbar -->
    <BatchSelectToolbar :count="batch.count" @clear="batch.clear()">
      <button @click="onBatchToggle(true)"
              class="px-3 h-8 text-xs text-white/90 hover:text-white hover:bg-white/10 rounded-md transition"
              :disabled="busyBatch">啟用</button>
      <button @click="onBatchToggle(false)"
              class="px-3 h-8 text-xs text-white/90 hover:text-white hover:bg-white/10 rounded-md transition"
              :disabled="busyBatch">停用</button>
      <button @click="onBatchExportExcel"
              class="px-3 h-8 text-xs text-white/90 hover:text-white hover:bg-white/10 rounded-md transition"
              :disabled="busyBatch">匯出 Excel</button>
      <button @click="onBatchExportZip"
              class="px-3 h-8 text-xs text-white/90 hover:text-white hover:bg-white/10 rounded-md transition"
              :disabled="busyBatch">匯出 ZIP</button>
      <button @click="onBatchDelete"
              class="px-3 h-8 text-xs text-danger-300 hover:text-danger-200 hover:bg-danger-500/20 rounded-md transition"
              :disabled="busyBatch">刪除</button>
    </BatchSelectToolbar>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { knowledgeApi } from '../../api/knowledge'
import { useBatchSelect } from '../../composables/useBatchSelect'
import BatchSelectToolbar from '../../components/common/BatchSelectToolbar.vue'
import {
  IconArrowLeft, IconCheck, IconDelete, IconDocument, IconFolder,
  IconImage, IconRefresh, IconSpinner, IconSpreadsheet, IconUpload, IconWarning,
} from '../../components/icons'

const route = useRoute()
const kbId = computed(() => route.params.kbId as string)

const docs = ref<any[]>([])
const loading = ref(false)
const dragging = ref(false)
const uploadingFile = ref<File | null>(null)
const uploadProgress = ref(0)
let pollTimer: any = null

async function loadDocs() {
  loading.value = true
  try {
    docs.value = await knowledgeApi.listDocuments(kbId.value)
  } catch (e) {
    console.error('listDocuments failed', e)
  } finally {
    loading.value = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(() => {
    if (docs.value.some(d => d.status === 'pending' || d.status === 'processing')) loadDocs()
  }, 3000)
}
function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

onMounted(() => { loadDocs(); startPolling() })
onBeforeUnmount(stopPolling)

async function onFileSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) await upload(file)
  input.value = ''
}

function onDrop(e: DragEvent) {
  dragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) upload(file)
}

async function upload(file: File) {
  uploadingFile.value = file
  uploadProgress.value = 0
  try {
    await knowledgeApi.uploadDocument(kbId.value, file, p => (uploadProgress.value = p))
    await loadDocs()
  } catch (e: any) {
    alert('上傳失敗：' + (e.response?.data?.detail || e.message))
  } finally {
    uploadingFile.value = null
    uploadProgress.value = 0
  }
}

async function onDelete(doc: any) {
  if (!confirm(`確定要刪除「${doc.name}」？`)) return
  try {
    await knowledgeApi.deleteDocument(doc.id)
    docs.value = docs.value.filter(d => d.id !== doc.id)
  } catch (e: any) {
    alert('刪除失敗：' + (e.response?.data?.detail || e.message))
  }
}

// ── Round 10 — MaxKB parity 操作 ─────────────────────────────────
function downloadUrl(doc: any): string {
  return knowledgeApi.downloadDocUrl?.(doc.id) ||
    `/api/v1/knowledge/documents/doc/${doc.id}/download`
}

async function onGenerateQuestions(doc: any) {
  if (!confirm(`對「${doc.name}」自動生成常見問題？\n會呼叫 LLM，可能需要幾十秒。`)) return
  try {
    const r = await knowledgeApi.generateDocQuestions(doc.id, { per_paragraph: 2, max_paragraphs: 20 })
    alert(`已產生 ${r?.questions?.length ?? 0} 個常見問題`)
  } catch (e: any) {
    alert('生成失敗：' + (e.response?.data?.detail || e.message))
  }
}

async function onExportExcel() {
  try {
    const blob = await knowledgeApi.exportExcel(kbId.value, [])
    _saveBlob(blob, `kb-${kbId.value}.xlsx`)
  } catch (e: any) {
    alert('匯出失敗：' + (e.response?.data?.detail || e.message))
  }
}

async function onExportZip() {
  try {
    const blob = await knowledgeApi.exportZip(kbId.value, [])
    _saveBlob(blob, `kb-${kbId.value}.zip`)
  } catch (e: any) {
    alert('匯出失敗：' + (e.response?.data?.detail || e.message))
  }
}

function _saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename
  document.body.appendChild(a); a.click()
  setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url) }, 100)
}

// ── v2.1 11-2：批量選擇 ───────────────────────────────────────────
const batch = useBatchSelect()
const busyBatch = ref(false)

const allDocIds = computed(() => docs.value.map((d: any) => d.id))
const allSelected = computed(() =>
  docs.value.length > 0 && docs.value.every((d: any) => batch.isSelected(d.id))
)
const someSelected = computed(() => batch.count.value > 0 && !allSelected.value)

function toggleAll() {
  if (allSelected.value) batch.clear()
  else batch.selectAll(allDocIds.value)
}

async function onBatchToggle(enabled: boolean) {
  if (!batch.hasSelection.value) return
  busyBatch.value = true
  try {
    await knowledgeApi.batchToggleDocs(kbId.value, Array.from(batch.selected.value), enabled)
    await loadDocs()
    batch.clear()
  } catch (e: any) {
    alert((enabled ? '啟用' : '停用') + '失敗：' + (e?.response?.data?.detail || e?.message))
  } finally {
    busyBatch.value = false
  }
}

async function onBatchDelete() {
  if (!batch.hasSelection.value) return
  if (!confirm(`確定刪除 ${batch.count.value} 個文件？此動作無法復原。`)) return
  busyBatch.value = true
  try {
    await knowledgeApi.batchDeleteDocs(kbId.value, Array.from(batch.selected.value))
    await loadDocs()
    batch.clear()
  } catch (e: any) {
    alert('刪除失敗：' + (e?.response?.data?.detail || e?.message))
  } finally {
    busyBatch.value = false
  }
}

async function onBatchExportExcel() {
  busyBatch.value = true
  try {
    const ids = batch.hasSelection.value ? Array.from(batch.selected.value) : []
    const blob = await knowledgeApi.exportExcel(kbId.value, ids)
    _saveBlob(blob, `kb-${kbId.value}-selected.xlsx`)
  } catch (e: any) {
    alert('匯出失敗：' + (e?.response?.data?.detail || e?.message))
  } finally {
    busyBatch.value = false
  }
}

async function onBatchExportZip() {
  busyBatch.value = true
  try {
    const ids = batch.hasSelection.value ? Array.from(batch.selected.value) : []
    const blob = await knowledgeApi.exportZip(kbId.value, ids)
    _saveBlob(blob, `kb-${kbId.value}-selected.zip`)
  } catch (e: any) {
    alert('匯出失敗：' + (e?.response?.data?.detail || e?.message))
  } finally {
    busyBatch.value = false
  }
}

// ─── UI helpers ────────────────────────────────────────────────
function fileTypeIcon(t: string) {
  const ext = (t || '').toLowerCase()
  if (['xlsx', 'xls', 'csv'].includes(ext)) return IconSpreadsheet
  if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext)) return IconImage
  return IconDocument
}
function fileTypeBg(t: string) {
  const ext = (t || '').toLowerCase()
  if (['pdf'].includes(ext))                     return 'bg-danger-50  text-danger-600'
  if (['doc', 'docx'].includes(ext))             return 'bg-info-50    text-info-600'
  if (['xlsx', 'xls', 'csv'].includes(ext))      return 'bg-success-50 text-success-600'
  if (['md', 'txt'].includes(ext))               return 'bg-neutral-100 text-neutral-600'
  return 'bg-neutral-100 text-neutral-600'
}

function formatSize(bytes: number): string {
  if (!bytes) return '—'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

function statusLabel(s: string): string {
  return { pending: '排隊中', processing: '處理中', ready: '完成', error: '失敗' }[s] || s
}
function statusChipClass(s: string): string {
  return {
    pending:    'bg-neutral-100 text-neutral-600',
    processing: 'bg-info-50    text-info-700',
    ready:      'bg-success-50 text-success-700',
    error:      'bg-danger-50  text-danger-600',
  }[s] || 'bg-neutral-100 text-neutral-500'
}
function statusDotClass(s: string): string {
  return {
    pending:    'bg-neutral-400',
    processing: 'bg-info-500    animate-pulse',
    ready:      'bg-success-500',
    error:      'bg-danger-500',
  }[s] || 'bg-neutral-400'
}
</script>
