<template>
  <div class="flex flex-col h-full overflow-hidden bg-gray-50">

    <!-- Header -->
    <div class="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between flex-shrink-0">
      <div class="flex items-center gap-3">
        <button @click="$router.push('/knowledge')"
                class="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
          </svg>
        </button>
        <div>
          <h2 class="text-base font-semibold text-gray-900">文件管理</h2>
          <p class="text-xs text-gray-400 font-mono">{{ kbId }}</p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <button @click="loadDocs" :disabled="loading"
                class="px-3 py-1.5 text-xs text-gray-600 bg-white border border-gray-200 rounded-lg hover:border-indigo-400 hover:text-indigo-600 transition disabled:opacity-50">
          🔄 重新整理
        </button>
        <button @click="$refs.fileInput.click()"
                class="px-4 py-1.5 bg-indigo-600 text-white text-xs font-semibold rounded-lg hover:bg-indigo-700 transition">
          + 上傳文件
        </button>
        <input ref="fileInput" type="file" class="hidden"
               accept=".pdf,.docx,.doc,.txt,.md,.xlsx,.csv"
               @change="onFileSelected" />
      </div>
    </div>

    <!-- Body -->
    <div class="flex-1 overflow-y-auto p-6"
         @dragover.prevent="dragging = true"
         @dragleave.prevent="dragging = false"
         @drop.prevent="onDrop">

      <!-- Drag overlay -->
      <div v-if="dragging"
           class="fixed inset-0 bg-indigo-500/10 backdrop-blur-sm border-4 border-dashed border-indigo-400 rounded-3xl flex items-center justify-center z-50 m-12 pointer-events-none">
        <div class="text-2xl font-semibold text-indigo-700">放開以上傳文件</div>
      </div>

      <!-- Empty -->
      <div v-if="!loading && docs.length === 0"
           class="bg-white border-2 border-dashed border-gray-200 rounded-2xl p-16 text-center">
        <div class="text-5xl mb-4 opacity-40">📂</div>
        <p class="text-gray-500 mb-2">尚未上傳任何文件</p>
        <p class="text-sm text-gray-400 mb-6">支援 PDF、DOCX、TXT、MD、XLSX、CSV，單檔上限 50MB</p>
        <button @click="$refs.fileInput.click()"
                class="px-5 py-2 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-700 transition">
          選擇文件
        </button>
      </div>

      <!-- Loading -->
      <div v-else-if="loading && docs.length === 0" class="text-center py-16 text-gray-400 text-sm">
        載入中…
      </div>

      <!-- Document list -->
      <div v-else class="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 border-b border-gray-100">
            <tr class="text-left text-xs text-gray-500 uppercase tracking-wider">
              <th class="px-5 py-3 font-semibold">文件</th>
              <th class="px-5 py-3 font-semibold w-32">狀態</th>
              <th class="px-5 py-3 font-semibold w-48">處理進度</th>
              <th class="px-5 py-3 font-semibold w-24">段落</th>
              <th class="px-5 py-3 font-semibold w-24">大小</th>
              <th class="px-5 py-3 font-semibold w-12"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="doc in docs" :key="doc.id"
                class="border-b border-gray-50 last:border-0 hover:bg-gray-50/50 transition">
              <td class="px-5 py-3">
                <div class="flex items-center gap-3">
                  <span class="text-lg">{{ fileTypeIcon(doc.file_type) }}</span>
                  <div class="min-w-0">
                    <div class="text-sm text-gray-900 truncate" :title="doc.name">{{ doc.name }}</div>
                    <div class="text-[11px] text-gray-400 font-mono">{{ doc.file_type }}</div>
                  </div>
                </div>
              </td>
              <td class="px-5 py-3">
                <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium"
                      :class="statusChipClass(doc.status)">
                  <span class="w-1.5 h-1.5 rounded-full" :class="statusDotClass(doc.status)"></span>
                  {{ statusLabel(doc.status) }}
                </span>
              </td>
              <td class="px-5 py-3">
                <div v-if="doc.status === 'processing' || doc.status === 'pending'" class="space-y-1">
                  <div class="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div class="h-full bg-indigo-500 transition-all duration-500"
                         :style="{ width: (doc.progress || 0) + '%' }"></div>
                  </div>
                  <p class="text-[11px] text-gray-500 truncate">{{ doc.progress_message || '等待中…' }}</p>
                </div>
                <p v-else-if="doc.status === 'error'" class="text-[11px] text-rose-500 truncate"
                   :title="doc.error_message">⚠️ {{ doc.error_message || '處理失敗' }}</p>
                <p v-else-if="doc.status === 'ready'" class="text-[11px] text-emerald-600">✓ 處理完成</p>
              </td>
              <td class="px-5 py-3 text-sm text-gray-600">
                {{ doc.paragraph_count || 0 }}
              </td>
              <td class="px-5 py-3 text-sm text-gray-600">
                {{ formatSize(doc.file_size) }}
              </td>
              <td class="px-5 py-3">
                <button @click="onDelete(doc)"
                        class="text-gray-300 hover:text-rose-500 transition p-1 rounded-lg hover:bg-rose-50"
                        title="刪除">
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                  </svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 上傳中 toast -->
      <transition
        enter-active-class="transition-all duration-300 ease-out"
        enter-from-class="opacity-0 translate-y-2"
        enter-to-class="opacity-100 translate-y-0"
        leave-active-class="transition-all duration-200 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div v-if="uploadingFile"
             class="fixed bottom-6 right-6 bg-white border border-gray-200 rounded-2xl shadow-lg p-4 w-80 z-50">
          <div class="flex items-center gap-3 mb-2">
            <span class="text-xl">📤</span>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-gray-900 truncate">{{ uploadingFile.name }}</p>
              <p class="text-[11px] text-gray-400">{{ uploadProgress }}% 上傳中…</p>
            </div>
          </div>
          <div class="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div class="h-full bg-indigo-500 transition-all" :style="{ width: uploadProgress + '%' }"></div>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { useRoute } from 'vue-router'
import { knowledgeApi } from '../../api/knowledge'

const route = useRoute()
const kbId  = computed(() => route.params.kbId as string)

const docs            = ref<any[]>([])
const loading         = ref(false)
const dragging        = ref(false)
const uploadingFile   = ref<File | null>(null)
const uploadProgress  = ref(0)

let pollTimer: any = null

// ─── 載入 / 自動輪詢 ─────────────────────────────────────────────────────────
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
    // 若有 pending/processing，每 3 秒輪詢
    if (docs.value.some(d => d.status === 'pending' || d.status === 'processing')) {
      loadDocs()
    }
  }, 3000)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

onMounted(() => {
  loadDocs()
  startPolling()
})

onBeforeUnmount(stopPolling)

// ─── 上傳 ─────────────────────────────────────────────────────────────────────
async function onFileSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file  = input.files?.[0]
  if (file) await upload(file)
  input.value = ''
}

function onDrop(e: DragEvent) {
  dragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) upload(file)
}

async function upload(file: File) {
  uploadingFile.value  = file
  uploadProgress.value = 0
  try {
    await knowledgeApi.uploadDocument(kbId.value, file, (p) => uploadProgress.value = p)
    await loadDocs()
  } catch (e: any) {
    alert('上傳失敗：' + (e.response?.data?.detail || e.message))
  } finally {
    uploadingFile.value  = null
    uploadProgress.value = 0
  }
}

// ─── 刪除 ─────────────────────────────────────────────────────────────────────
async function onDelete(doc: any) {
  if (!confirm(`確定要刪除「${doc.name}」嗎？`)) return
  try {
    await knowledgeApi.deleteDocument(doc.id)
    docs.value = docs.value.filter(d => d.id !== doc.id)
  } catch (e: any) {
    alert('刪除失敗：' + (e.response?.data?.detail || e.message))
  }
}

// ─── UI helpers ────────────────────────────────────────────────────────────────
function fileTypeIcon(t: string): string {
  const map: Record<string, string> = {
    pdf: '📕', doc: '📘', docx: '📘',
    txt: '📄', md: '📝',
    xlsx: '📊', xls: '📊', csv: '📊',
  }
  return map[t?.toLowerCase()] || '📄'
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
    pending:    'bg-gray-100 text-gray-600',
    processing: 'bg-blue-50 text-blue-700',
    ready:      'bg-emerald-50 text-emerald-700',
    error:      'bg-rose-50 text-rose-600',
  }[s] || 'bg-gray-100 text-gray-500'
}
function statusDotClass(s: string): string {
  return {
    pending:    'bg-gray-400',
    processing: 'bg-blue-500 animate-pulse',
    ready:      'bg-emerald-500',
    error:      'bg-rose-500',
  }[s] || 'bg-gray-400'
}
</script>
