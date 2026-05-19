<template>
  <div class="flex flex-col h-full bg-surface-base">
    <!-- 頂部 -->
    <div class="px-6 py-4 border-b border-bd bg-surface-raised flex items-center justify-between flex-shrink-0">
      <div class="flex items-center gap-3 min-w-0">
        <button
          @click="$router.back()"
          class="p-1.5 rounded-lg text-fg-secondary hover:bg-neutral-200/60 hover:text-fg"
          aria-label="返回"
        >
          <SIcon name="arrow-left" :size="16" />
        </button>
        <div class="min-w-0">
          <h1 class="text-base font-semibold text-fg truncate">{{ docName || '段落' }}</h1>
          <p class="text-xs text-fg-secondary mt-0.5">
            共 {{ paragraphs.length }} 段
            <span v-if="filtered.length !== paragraphs.length"> · 顯示 {{ filtered.length }} 段</span>
          </p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <button @click="addModal.open = true"
                class="h-8 px-3 text-xs text-fg bg-surface-raised border border-bd rounded-lg hover:border-brand-400 hover:text-brand-600 flex items-center gap-1">
          <SIcon name="plus" :size="14" /> 新增段落
        </button>
        <button @click="onGenerateAll" :disabled="generating"
                class="h-8 px-3 text-xs text-fg bg-surface-raised border border-bd rounded-lg hover:border-brand-400 hover:text-brand-600 disabled:opacity-50">
          {{ generating ? '生成中…' : '為文件產生 Q&A' }}
        </button>
        <button @click="refresh"
                class="h-8 px-3 text-xs text-fg bg-surface-raised border border-bd rounded-lg hover:border-brand-400 hover:text-brand-600 flex items-center gap-1">
          <SIcon name="refresh" :size="14" /> 重新整理
        </button>
      </div>
    </div>

    <!-- 篩選列 -->
    <div class="px-6 py-3 border-b border-bd bg-surface-raised flex items-center gap-3 flex-shrink-0">
      <div class="relative flex-1 max-w-md">
        <SIcon name="search" :size="14" class="absolute left-2.5 top-1/2 -translate-y-1/2 text-fg-secondary" />
        <input v-model="searchQuery" type="text" placeholder="搜尋段落內容…"
               class="w-full h-8 pl-8 pr-3 text-xs bg-surface-base border border-bd rounded-lg focus:outline-none focus:border-brand-400" />
      </div>
      <select v-model="statusFilter"
              class="h-8 px-2 text-xs bg-surface-base border border-bd rounded-lg focus:outline-none focus:border-brand-400">
        <option value="all">全部狀態</option>
        <option value="active">啟用</option>
        <option value="inactive">停用</option>
        <option value="unindexed">未索引</option>
      </select>
      <label class="text-xs text-fg-secondary flex items-center gap-1.5 cursor-pointer">
        <input type="checkbox" :checked="allSelected" @change="toggleAllSelected" class="rounded" />
        全選
      </label>
    </div>

    <!-- 段落列表 -->
    <div class="flex-1 overflow-y-auto p-6 space-y-3 pb-32">
      <p v-if="loading" class="text-sm text-fg-secondary text-center py-12">載入中…</p>
      <p v-else-if="!filtered.length && paragraphs.length" class="text-sm text-fg-secondary text-center py-12">
        無符合條件的段落
      </p>
      <p v-else-if="!paragraphs.length" class="text-sm text-fg-secondary text-center py-12">
        此文件尚無段落。點選右上「新增段落」開始建立。
      </p>
      <div
        v-for="p in filtered"
        :key="p.id"
        :class="['group relative border rounded-xl p-4 transition bg-surface-raised',
                 selected.has(p.id) ? 'border-brand-400 ring-2 ring-brand-100' : 'border-bd hover:border-neutral-300']"
      >
        <div class="flex items-start gap-3">
          <input type="checkbox" :checked="selected.has(p.id)" @change="toggleSelect(p.id)"
                 class="mt-1.5 rounded" />
          <div class="flex-1 min-w-0">
            <!-- metadata bar -->
            <div class="flex items-center gap-2 mb-2 flex-wrap">
              <span class="text-[11px] text-fg-secondary font-mono">#{{ p.order_index + 1 }}</span>
              <span :class="['text-[10px] px-1.5 py-0.5 rounded inline-flex items-center gap-0.5',
                              p.is_active ? 'bg-success-50 text-success-700' : 'bg-neutral-200 text-fg-secondary']">
                <SIcon :name="p.is_active ? 'check-circle' : 'eye-off'" :size="10" />
                {{ p.is_active ? '啟用' : '停用' }}
              </span>
              <span class="text-[10px] px-1.5 py-0.5 bg-neutral-200 text-fg-secondary rounded">
                {{ p.char_count }} 字
              </span>
              <span :class="['text-[10px] px-1.5 py-0.5 rounded inline-flex items-center gap-0.5',
                              p.has_embedding ? 'bg-brand-50 text-brand-700' : 'bg-warning-50 text-warning-700']">
                <SIcon :name="p.has_embedding ? 'check' : 'alert-triangle'" :size="10" />
                {{ p.has_embedding ? '已索引' : '未索引' }}
              </span>
              <span v-if="(p.qa_pairs?.length || 0) > 0"
                    class="text-[10px] px-1.5 py-0.5 bg-brand-50 text-brand-700 rounded">
                {{ p.qa_pairs.length }} 個 Q&A
              </span>
              <span v-if="p.title" class="text-[12px] font-medium text-fg">{{ p.title }}</span>
            </div>

            <!-- content -->
            <p v-if="editingId !== p.id" class="text-sm text-fg whitespace-pre-wrap line-clamp-6">{{ p.content }}</p>
            <div v-else class="space-y-2">
              <input v-model="editDraft.title" placeholder="標題（選填）"
                     class="w-full h-8 px-3 text-xs bg-surface-base border border-bd rounded-lg focus:outline-none focus:border-brand-400" />
              <textarea v-model="editDraft.content" rows="6"
                        class="w-full px-3 py-2 text-sm bg-surface-base border border-bd rounded-lg focus:outline-none focus:border-brand-400" />
              <div class="flex gap-2 justify-end">
                <button @click="editingId = null"
                        class="h-7 px-3 text-xs text-fg-secondary hover:text-fg">取消</button>
                <button @click="saveEdit(p)" :disabled="busyId === p.id"
                        class="h-7 px-3 text-xs text-white bg-brand-600 rounded-lg hover:bg-brand-700 disabled:opacity-50">
                  儲存
                </button>
              </div>
            </div>

            <!-- 操作 buttons -->
            <div v-if="editingId !== p.id" class="flex items-center gap-1 mt-3 flex-wrap">
              <ActionBtn icon="edit" label="編輯" @click="startEdit(p)" />
              <ActionBtn icon="copy" label="分割" @click="openSplit(p)" />
              <ActionBtn :icon="p.is_active ? 'eye-off' : 'eye'"
                         :label="p.is_active ? '停用' : '啟用'"
                         @click="onToggle(p)" />
              <ActionBtn icon="trash" label="刪除" danger @click="onDelete(p)" />
              <ActionBtn icon="search" label="命中測試" @click="openHitTest(p)" />
              <ActionBtn icon="message-square" label="Q&A" @click="generateOne(p.id)" :loading="busyQA === p.id" />
              <span class="flex-1"></span>
              <ActionBtn icon="chevron-up" title="上移" iconOnly @click="moveBtn(p.id, 'up')" />
              <ActionBtn icon="chevron-down" title="下移" iconOnly @click="moveBtn(p.id, 'down')" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- floating bulk bar -->
    <transition enter-active-class="transition duration-200" enter-from-class="opacity-0 translate-y-2"
                leave-active-class="transition duration-150" leave-to-class="opacity-0 translate-y-2">
      <div v-if="selected.size > 0"
           class="fixed bottom-6 left-1/2 -translate-x-1/2 z-30 bg-surface-raised border border-bd shadow-xl rounded-xl px-4 py-3 flex items-center gap-3">
        <span class="text-xs text-fg font-medium">已選 {{ selected.size }} 段</span>
        <span class="w-px h-5 bg-bd"></span>
        <button @click="onBulk('enable')" class="h-7 px-2.5 text-xs text-fg hover:bg-neutral-200/60 rounded">批次啟用</button>
        <button @click="onBulk('disable')" class="h-7 px-2.5 text-xs text-fg hover:bg-neutral-200/60 rounded">批次停用</button>
        <button @click="onBulk('regen_embedding')" class="h-7 px-2.5 text-xs text-fg hover:bg-neutral-200/60 rounded">重建向量</button>
        <button v-if="selected.size >= 2" @click="onBulkMerge"
                class="h-7 px-2.5 text-xs text-brand-700 hover:bg-brand-50 rounded">合併</button>
        <button @click="onBulk('delete')" class="h-7 px-2.5 text-xs text-danger-700 hover:bg-danger-50 rounded">批次刪除</button>
        <span class="w-px h-5 bg-bd"></span>
        <button @click="selected.clear()" class="h-7 px-2 text-xs text-fg-secondary hover:text-fg">取消</button>
      </div>
    </transition>

    <!-- 新增段落 Modal -->
    <ModalShell v-if="addModal.open" title="新增段落" @close="addModal.open = false">
      <div class="space-y-3">
        <input v-model="addModal.title" placeholder="標題（選填）"
               class="w-full h-9 px-3 text-sm bg-surface-base border border-bd rounded-lg focus:outline-none focus:border-brand-400" />
        <textarea v-model="addModal.content" rows="8" placeholder="段落內容…"
                  class="w-full px-3 py-2 text-sm bg-surface-base border border-bd rounded-lg focus:outline-none focus:border-brand-400" />
        <p class="text-[11px] text-fg-secondary">儲存後會立刻為此段建立向量索引。</p>
      </div>
      <template #footer>
        <button @click="addModal.open = false" class="h-8 px-3 text-xs text-fg-secondary hover:text-fg">取消</button>
        <button @click="doAdd" :disabled="!addModal.content.trim() || addModal.busy"
                class="h-8 px-3 text-xs text-white bg-brand-600 rounded-lg hover:bg-brand-700 disabled:opacity-50">
          {{ addModal.busy ? '建立中…' : '新增' }}
        </button>
      </template>
    </ModalShell>

    <!-- 分割段落 Modal -->
    <ModalShell v-if="splitModal.open" title="分割段落" @close="splitModal.open = false" wide>
      <div class="space-y-3">
        <div class="flex items-center gap-2">
          <label class="text-xs text-fg-secondary">分隔符</label>
          <select v-model="splitModal.sepKey" @change="recomputeSplit"
                  class="h-7 px-2 text-xs bg-surface-base border border-bd rounded-lg">
            <option value="dbl_nl">空行（\\n\\n）</option>
            <option value="nl">換行（\\n）</option>
            <option value="period">中文句號（。）</option>
            <option value="custom">自訂</option>
          </select>
          <input v-if="splitModal.sepKey === 'custom'" v-model="splitModal.customSep" @input="recomputeSplit"
                 class="flex-1 h-7 px-2 text-xs bg-surface-base border border-bd rounded-lg" placeholder="例：---" />
        </div>
        <div class="text-xs text-fg-secondary">預覽（共 {{ splitModal.preview.length }} 段）：</div>
        <div class="max-h-80 overflow-y-auto space-y-2">
          <div v-for="(s, i) in splitModal.preview" :key="i"
               class="p-2 border border-bd rounded text-xs text-fg bg-surface-base whitespace-pre-wrap">
            <span class="text-fg-secondary font-mono">#{{ i + 1 }}</span> {{ s }}
          </div>
        </div>
      </div>
      <template #footer>
        <button @click="splitModal.open = false" class="h-8 px-3 text-xs text-fg-secondary hover:text-fg">取消</button>
        <button @click="doSplit" :disabled="splitModal.preview.length < 2 || splitModal.busy"
                class="h-8 px-3 text-xs text-white bg-brand-600 rounded-lg hover:bg-brand-700 disabled:opacity-50">
          {{ splitModal.busy ? '處理中…' : `分割為 ${splitModal.preview.length} 段` }}
        </button>
      </template>
    </ModalShell>

    <!-- 命中測試 Modal -->
    <ModalShell v-if="hitModal.open" :title="`命中測試 #${(hitModal.paragraph?.order_index ?? 0) + 1}`" @close="hitModal.open = false">
      <div class="space-y-3">
        <textarea v-model="hitModal.query" rows="3" placeholder="輸入測試查詢…"
                  class="w-full px-3 py-2 text-sm bg-surface-base border border-bd rounded-lg focus:outline-none focus:border-brand-400" />
        <button @click="runHitTest" :disabled="!hitModal.query.trim() || hitModal.busy"
                class="h-8 px-3 text-xs text-white bg-brand-600 rounded-lg hover:bg-brand-700 disabled:opacity-50">
          {{ hitModal.busy ? '計算中…' : '執行' }}
        </button>
        <div v-if="hitModal.result" class="p-3 rounded-lg bg-neutral-200/40 border border-bd">
          <div v-if="hitModal.result.score !== null" class="text-sm text-fg">
            相似度：<span class="font-mono font-semibold text-brand-700">{{ (hitModal.result.score * 100).toFixed(2) }}%</span>
            <span class="text-xs text-fg-secondary ml-2">（cosine similarity）</span>
          </div>
          <div v-else class="text-sm text-warning-700">
            該段落尚未向量化，無法計算相似度。
          </div>
        </div>
      </div>
      <template #footer>
        <button @click="hitModal.open = false" class="h-8 px-3 text-xs text-fg-secondary hover:text-fg">關閉</button>
      </template>
    </ModalShell>

    <!-- toast -->
    <transition enter-active-class="transition duration-200" enter-from-class="opacity-0 translate-y-2"
                leave-active-class="transition duration-150" leave-to-class="opacity-0 translate-y-2">
      <div v-if="toast"
           class="fixed bottom-24 left-1/2 -translate-x-1/2 z-40 bg-neutral-900 text-white text-xs px-4 py-2 rounded-lg shadow-lg">
        {{ toast }}
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { SIcon } from '@staffkm/ui-kit'
import { knowledgeApi } from '../../api/knowledge'
import { http } from '../../api/index'

interface Paragraph {
  id: string
  content: string
  title: string | null
  order_index: number
  char_count: number
  is_active: boolean
  qa_pairs: any[]
  has_embedding: boolean
}

const route = useRoute()
const docId = route.params.docId as string

const paragraphs = ref<Paragraph[]>([])
const loading = ref(true)
const generating = ref(false)
const busyQA = ref<string | null>(null)
const busyId = ref<string | null>(null)
const docName = ref('')
const toast = ref('')

function flash(msg: string) {
  toast.value = msg
  setTimeout(() => { if (toast.value === msg) toast.value = '' }, 2400)
}

// ── 篩選 ────────────────────────────────────────────────────────────
const searchQuery = ref('')
const statusFilter = ref<'all' | 'active' | 'inactive' | 'unindexed'>('all')

const filtered = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  return paragraphs.value.filter(p => {
    if (statusFilter.value === 'active' && !p.is_active) return false
    if (statusFilter.value === 'inactive' && p.is_active) return false
    if (statusFilter.value === 'unindexed' && p.has_embedding) return false
    if (q && !p.content.toLowerCase().includes(q) && !(p.title || '').toLowerCase().includes(q)) return false
    return true
  })
})

// ── 選取 ────────────────────────────────────────────────────────────
const selected = reactive(new Set<string>())
function toggleSelect(id: string) {
  if (selected.has(id)) selected.delete(id)
  else selected.add(id)
}
const allSelected = computed(() => filtered.value.length > 0 && filtered.value.every(p => selected.has(p.id)))
function toggleAllSelected() {
  if (allSelected.value) filtered.value.forEach(p => selected.delete(p.id))
  else filtered.value.forEach(p => selected.add(p.id))
}

// ── 載入 ────────────────────────────────────────────────────────────
async function refresh() {
  loading.value = true
  try {
    const { data } = await http.get(`/knowledge/paragraphs/${docId}`)
    paragraphs.value = data?.data || []
  } catch (e: any) {
    flash('讀取段落失敗：' + (e?.response?.data?.detail || e?.message))
  } finally {
    loading.value = false
  }
}

// ── 編輯 ────────────────────────────────────────────────────────────
const editingId = ref<string | null>(null)
const editDraft = reactive({ content: '', title: '' })
function startEdit(p: Paragraph) {
  editingId.value = p.id
  editDraft.content = p.content
  editDraft.title = p.title || ''
}
async function saveEdit(p: Paragraph) {
  busyId.value = p.id
  try {
    await knowledgeApi.updateParagraph(p.id, {
      content: editDraft.content, title: editDraft.title || undefined,
    })
    editingId.value = null
    flash('已儲存')
    await refresh()
  } catch (e: any) {
    flash('儲存失敗：' + (e?.response?.data?.detail || e?.message))
  } finally {
    busyId.value = null
  }
}

// ── 啟用 / 停用 / 刪除 ───────────────────────────────────────────────
async function onToggle(p: Paragraph) {
  try {
    const r = await knowledgeApi.toggleParagraph(p.id)
    p.is_active = r?.is_active ?? !p.is_active
    flash(p.is_active ? '已啟用' : '已停用')
  } catch (e: any) {
    flash('切換失敗：' + (e?.response?.data?.detail || e?.message))
  }
}
async function onDelete(p: Paragraph) {
  if (!confirm(`確定刪除段落 #${p.order_index + 1}？此操作無法復原。`)) return
  try {
    await knowledgeApi.deleteParagraph(p.id)
    selected.delete(p.id)
    flash('已刪除')
    await refresh()
  } catch (e: any) {
    flash('刪除失敗：' + (e?.response?.data?.detail || e?.message))
  }
}

// ── 移動 ────────────────────────────────────────────────────────────
async function moveBtn(pid: string, direction: 'up' | 'down' | 'top' | 'bottom') {
  try {
    await knowledgeApi.moveParagraph(pid, direction)
    await refresh()
  } catch (e: any) {
    flash('移動失敗：' + (e?.response?.data?.detail || e?.message))
  }
}

// ── 新增 Modal ──────────────────────────────────────────────────────
const addModal = reactive({ open: false, content: '', title: '', busy: false })
async function doAdd() {
  addModal.busy = true
  try {
    await knowledgeApi.addParagraph(docId, {
      content: addModal.content, title: addModal.title || undefined,
    })
    addModal.open = false
    addModal.content = ''
    addModal.title = ''
    flash('段落已新增')
    await refresh()
  } catch (e: any) {
    flash('新增失敗：' + (e?.response?.data?.detail || e?.message))
  } finally {
    addModal.busy = false
  }
}

// ── 分割 Modal ──────────────────────────────────────────────────────
const splitModal = reactive({
  open: false, paragraph: null as Paragraph | null, busy: false,
  sepKey: 'dbl_nl' as 'dbl_nl' | 'nl' | 'period' | 'custom',
  customSep: '', preview: [] as string[],
})
function openSplit(p: Paragraph) {
  splitModal.paragraph = p
  splitModal.sepKey = 'dbl_nl'
  splitModal.customSep = ''
  splitModal.open = true
  recomputeSplit()
}
function _sep(): string {
  switch (splitModal.sepKey) {
    case 'dbl_nl': return '\n\n'
    case 'nl': return '\n'
    case 'period': return '。'
    default: return splitModal.customSep || '\n\n'
  }
}
function recomputeSplit() {
  if (!splitModal.paragraph) { splitModal.preview = []; return }
  const sep = _sep()
  splitModal.preview = splitModal.paragraph.content.split(sep).map(s => s.trim()).filter(Boolean)
}
async function doSplit() {
  if (!splitModal.paragraph) return
  splitModal.busy = true
  try {
    await knowledgeApi.splitParagraph(splitModal.paragraph.id, { separator: _sep() })
    splitModal.open = false
    flash('已分割')
    await refresh()
  } catch (e: any) {
    flash('分割失敗：' + (e?.response?.data?.detail || e?.message))
  } finally {
    splitModal.busy = false
  }
}

// ── 命中測試 Modal ──────────────────────────────────────────────────
const hitModal = reactive({
  open: false, paragraph: null as Paragraph | null, query: '',
  busy: false, result: null as { score: number | null } | null,
})
function openHitTest(p: Paragraph) {
  hitModal.paragraph = p
  hitModal.query = ''
  hitModal.result = null
  hitModal.open = true
}
async function runHitTest() {
  if (!hitModal.paragraph) return
  hitModal.busy = true
  try {
    const r = await knowledgeApi.hitTestParagraph(hitModal.paragraph.id, hitModal.query)
    hitModal.result = { score: r?.score ?? null }
  } catch (e: any) {
    flash('命中測試失敗：' + (e?.response?.data?.detail || e?.message))
  } finally {
    hitModal.busy = false
  }
}

// ── 批次 ────────────────────────────────────────────────────────────
async function onBulk(action: 'delete' | 'enable' | 'disable' | 'regen_embedding') {
  const ids = Array.from(selected)
  if (!ids.length) return
  if (action === 'delete' && !confirm(`確定刪除 ${ids.length} 段？此操作無法復原。`)) return
  try {
    const r = await knowledgeApi.bulkParagraphAction(action, ids)
    flash(`完成（影響 ${r?.affected ?? r?.queued ?? ids.length} 段）`)
    selected.clear()
    await refresh()
  } catch (e: any) {
    flash('批次操作失敗：' + (e?.response?.data?.detail || e?.message))
  }
}
async function onBulkMerge() {
  const ids = Array.from(selected)
  if (ids.length < 2) return
  // 依 order_index 排序合併
  const ordered = ids
    .map(id => paragraphs.value.find(p => p.id === id)!)
    .filter(Boolean)
    .sort((a, b) => a.order_index - b.order_index)
    .map(p => p.id)
  if (!confirm(`將 ${ordered.length} 段依順序合併為一段？其餘段落會被刪除。`)) return
  try {
    await knowledgeApi.mergeParagraphs(ordered)
    flash('已合併')
    selected.clear()
    await refresh()
  } catch (e: any) {
    flash('合併失敗：' + (e?.response?.data?.detail || e?.message))
  }
}

// ── Q&A 生成 ────────────────────────────────────────────────────────
async function generateOne(pid: string) {
  busyQA.value = pid
  try {
    const r = await knowledgeApi.generateParagraphQA(pid, { n: 3 })
    const idx = paragraphs.value.findIndex(p => p.id === pid)
    if (idx >= 0) paragraphs.value[idx] = { ...paragraphs.value[idx], qa_pairs: r?.qa_pairs || [] }
    flash('Q&A 已生成')
  } catch (e: any) {
    flash('Q&A 生成失敗：' + (e?.response?.data?.detail || e?.message))
  } finally {
    busyQA.value = null
  }
}

async function onGenerateAll() {
  if (!confirm('對所有段落跑 Q&A 生成？會呼叫 LLM 多次，可能需要 1~2 分鐘。')) return
  generating.value = true
  try {
    const r = await knowledgeApi.generateDocQuestions(docId, { per_paragraph: 2, max_paragraphs: 50 })
    flash(`已處理 ${r?.processed ?? 0} 段；共 ${r?.questions?.length ?? 0} 個常見問題`)
    await refresh()
  } catch (e: any) {
    flash('生成失敗：' + (e?.response?.data?.detail || e?.message))
  } finally {
    generating.value = false
  }
}

onMounted(refresh)

// ── 內聯小元件 ──────────────────────────────────────────────────────
const ActionBtn = (props: {
  icon: string; label?: string; title?: string; iconOnly?: boolean;
  danger?: boolean; loading?: boolean;
}, { emit, slots }: any) => {
  const cls = [
    'h-7 px-2 text-[11px] rounded inline-flex items-center gap-1 transition',
    props.danger
      ? 'text-danger-700 hover:bg-danger-50'
      : 'text-fg-secondary hover:text-brand-700 hover:bg-brand-50',
    props.loading ? 'opacity-50 pointer-events-none' : '',
  ].join(' ')
  return h('button', { class: cls, title: props.title || props.label, onClick: (e: Event) => emit('click', e) }, [
    h(SIcon, { name: props.icon, size: 12 }),
    !props.iconOnly && props.label ? props.label : null,
  ])
}
ActionBtn.props = ['icon', 'label', 'title', 'iconOnly', 'danger', 'loading']
ActionBtn.emits = ['click']

const ModalShell = (props: { title: string; wide?: boolean }, { emit, slots }: any) => {
  return h('div', {
    class: 'fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4',
    onClick: (e: MouseEvent) => { if (e.target === e.currentTarget) emit('close') },
  }, [
    h('div', { class: `bg-surface-raised border border-bd rounded-2xl shadow-2xl w-full ${props.wide ? 'max-w-2xl' : 'max-w-lg'}` }, [
      h('div', { class: 'px-5 py-3 border-b border-bd flex items-center justify-between' }, [
        h('h2', { class: 'text-sm font-semibold text-fg' }, props.title),
        h('button', { class: 'p-1 rounded text-fg-secondary hover:text-fg hover:bg-neutral-200/60', onClick: () => emit('close') },
          [h(SIcon, { name: 'x', size: 16 })]),
      ]),
      h('div', { class: 'p-5' }, slots.default?.()),
      slots.footer ? h('div', { class: 'px-5 py-3 border-t border-bd flex items-center justify-end gap-2 bg-surface-base/40' }, slots.footer()) : null,
    ]),
  ])
}
ModalShell.props = ['title', 'wide']
ModalShell.emits = ['close']
</script>