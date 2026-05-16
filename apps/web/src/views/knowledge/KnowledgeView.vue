<template>
  <div class="flex h-full">
    <!-- 左側資料夾樹（C-3）-->
    <aside class="w-60 border-r border-neutral-200 bg-surface-raised flex flex-col flex-shrink-0">
      <div class="px-3 py-3 border-b border-neutral-100 flex items-center justify-between">
        <h2 class="text-xs font-semibold uppercase tracking-widest text-neutral-500">
          資料夾
        </h2>
        <button
          @click="showNewFolder = true"
          class="w-6 h-6 flex items-center justify-center rounded-md text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700 transition"
          title="新增資料夾"
        >
          <IconPlus :size="12" :stroke-width="2.5" />
        </button>
      </div>

      <nav class="flex-1 overflow-y-auto py-2 px-2">
        <!-- 根目錄 -->
        <button
          @click="activeFolderId = null"
          class="w-full flex items-center gap-1 px-2 py-1.5 rounded-md text-sm transition-colors mb-0.5"
          :class="activeFolderId === null
            ? 'bg-neutral-100 text-neutral-900'
            : 'text-neutral-700 hover:bg-neutral-50'"
        >
          <span class="w-4 h-4"></span>
          <svg class="w-3.5 h-3.5 text-neutral-400" fill="currentColor" viewBox="0 0 24 24">
            <path d="M10 4H4a2 2 0 00-2 2v12a2 2 0 002 2h16a2 2 0 002-2V8a2 2 0 00-2-2h-8l-2-2z"/>
          </svg>
          <span class="truncate flex-1 text-left">所有知識庫</span>
          <span class="text-[10px] text-neutral-400">{{ kbs.length }}</span>
        </button>

        <FolderTree
          :nodes="folderTreeData"
          :active-id="activeFolderId"
          @select="(n) => activeFolderId = n.id"
        />
      </nav>
    </aside>

    <!-- 主內容 -->
    <div class="flex-1 flex flex-col">
      <!-- 頁首 -->
      <div class="px-6 py-5 border-b border-neutral-200 bg-surface-raised flex items-center justify-between flex-shrink-0">
        <div>
          <h1 class="text-lg font-semibold text-neutral-900">{{ activeFolderName }}</h1>
          <p class="text-xs text-neutral-500 mt-0.5">{{ $t('knowledge.docCount', { n: filteredKbs.length }) }}</p>
          <!-- D-6：Project 過濾指示 -->
          <div
            v-if="activeProject"
            class="mt-2 inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-brand-50 text-brand-700 text-[11px]"
          >
            <span>{{ activeProject.emoji || '#' }}</span>
            <span>Project：{{ activeProject.name }}</span>
            <button @click="projects.switchTo(null)" class="text-brand-500 hover:text-brand-700">×</button>
          </div>
        </div>
        <button
          @click="showCreate = true"
          class="inline-flex items-center gap-1.5 h-9 px-4 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-lg transition-colors shadow-sm"
        >
          <IconPlus :size="14" :stroke-width="2.5" />
          {{ $t('knowledge.createKb') }}
        </button>
      </div>

      <!-- 列表 -->
      <div class="flex-1 overflow-auto p-6">
        <div v-if="loading" class="flex items-center justify-center py-20 text-neutral-400 gap-2 text-sm">
          <IconSpinner :size="16" /> 載入中
        </div>

        <div v-else-if="!filteredKbs.length" class="flex flex-col items-center justify-center py-20">
          <div class="w-16 h-16 rounded-full bg-neutral-100 flex items-center justify-center text-neutral-400 mb-4">
            <IconKnowledge :size="28" :stroke-width="1.5" />
          </div>
          <p class="text-sm font-medium text-neutral-700 mb-1">尚未建立知識庫</p>
          <p class="text-xs text-neutral-500 mb-5 max-w-xs text-center">
            建立一個知識庫，再上傳文件、設定檢索方式
          </p>
          <button
            @click="showCreate = true"
            class="inline-flex items-center gap-1.5 h-9 px-4 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-lg transition-colors"
          >
            <IconPlus :size="14" :stroke-width="2.5" />
            建立第一個
          </button>
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <div
            v-for="kb in filteredKbs"
            :key="kb.id"
            class="relative bg-surface-raised rounded-xl border hover:shadow-md transition-all overflow-hidden group"
            :class="batch.isSelected(kb.id)
              ? 'border-brand-400 ring-1 ring-brand-200'
              : 'border-neutral-200 hover:border-brand-300'"
          >
            <button
              class="absolute top-3 right-3 z-10 w-5 h-5 flex items-center justify-center rounded border transition opacity-0 group-hover:opacity-100"
              :class="batch.isSelected(kb.id)
                ? 'bg-brand-600 border-brand-600 text-white opacity-100'
                : 'bg-white border-neutral-300 hover:border-brand-400 text-transparent'"
              @click.stop="batch.toggle(kb.id)"
            >
              <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
              </svg>
            </button>

            <div class="px-5 pt-5 pb-4">
              <div class="flex items-start justify-between mb-3 gap-3">
                <div class="flex items-start gap-3 min-w-0">
                  <div class="w-9 h-9 rounded-lg flex items-center justify-center text-brand-600 bg-brand-50 flex-shrink-0">
                    <IconKnowledge :size="18" />
                  </div>
                  <div class="min-w-0">
                    <h3 class="font-semibold text-sm text-neutral-900 truncate">{{ kb.name }}</h3>
                    <p class="text-[11px] text-neutral-400 mt-0.5 font-mono">{{ kb.id.slice(0, 8) }}</p>
                  </div>
                </div>
                <span class="text-[11px] px-2 py-0.5 rounded-full font-medium flex-shrink-0" :class="statusClass(kb.status)">
                  {{ statusLabel(kb.status) }}
                </span>
              </div>
              <p class="text-xs text-neutral-500 line-clamp-2 min-h-[32px]">
                {{ kb.description || '尚未填寫說明' }}
              </p>
            </div>
            <div class="px-3 pb-3 pt-0 flex gap-1.5">
              <router-link
                :to="`/knowledge/${kb.id}/documents`"
                class="flex-1 text-center text-xs font-medium text-neutral-700 bg-neutral-100 hover:bg-neutral-200 py-1.5 rounded-md transition-colors"
              >文件</router-link>
              <router-link
                :to="`/knowledge/${kb.id}/hit-test`"
                class="flex-1 text-center text-xs font-medium text-neutral-700 bg-neutral-100 hover:bg-neutral-200 py-1.5 rounded-md transition-colors"
              >檢索測試</router-link>
              <button
                @click="deleteKB(kb.id)"
                class="px-2 text-neutral-400 hover:text-danger-600 hover:bg-danger-50 rounded-md transition-colors"
                title="刪除"
              >
                <IconDelete :size="14" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 建立 KB Modal -->
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0"
      leave-active-class="transition duration-150 ease-in"
      leave-to-class="opacity-0"
    >
      <div
        v-if="showCreate"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-900/40 backdrop-blur-sm"
        @click.self="showCreate = false"
      >
        <div class="w-full max-w-md bg-surface-raised rounded-2xl shadow-2xl overflow-hidden">
          <div class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between">
            <h3 class="font-semibold text-base text-neutral-900">建立知識庫</h3>
            <button @click="showCreate = false" class="p-1 rounded-md text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100">
              <IconClose :size="14" />
            </button>
          </div>
          <div class="px-5 py-4 space-y-4">
            <div>
              <label class="block text-xs font-semibold text-neutral-600 mb-1.5">
                名稱 <span class="text-danger-500">*</span>
              </label>
              <input
                v-model="form.name"
                type="text"
                placeholder="例：人事法規、採購規範"
                class="w-full text-sm border border-neutral-200 rounded-lg px-3 py-2 focus:outline-none focus:border-brand-500 focus:shadow-focus"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold text-neutral-600 mb-1.5">說明</label>
              <textarea
                v-model="form.description"
                rows="3"
                placeholder="這個知識庫的用途、適用對象等"
                class="w-full text-sm border border-neutral-200 rounded-lg px-3 py-2 focus:outline-none focus:border-brand-500 focus:shadow-focus resize-none"
              />
            </div>

            <!-- 切片策略（RFC-006）─────────────────────────────────── -->
            <div>
              <label class="block text-xs font-semibold text-neutral-600 mb-1.5">
                切片策略
              </label>
              <div class="grid grid-cols-2 gap-2">
                <button
                  v-for="opt in CHUNK_STRATEGIES" :key="opt.value"
                  type="button"
                  @click="form.chunk_strategy = opt.value"
                  class="text-left px-3 py-2 rounded-lg border text-xs transition"
                  :class="form.chunk_strategy === opt.value
                    ? 'border-brand-400 bg-brand-50 text-brand-700'
                    : 'border-neutral-200 hover:border-brand-300 text-neutral-700'"
                >
                  <div class="font-semibold">{{ opt.label }}</div>
                  <div class="text-[10px] text-neutral-500 mt-0.5">{{ opt.desc }}</div>
                </button>
              </div>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-xs font-semibold text-neutral-600 mb-1">每段字數</label>
                <input
                  v-model.number="form.chunk_size" type="number" min="128" max="2048"
                  class="w-full text-sm h-9 px-3 rounded-md border border-neutral-200 focus:outline-none focus:ring-1 focus:ring-brand-400"
                />
              </div>
              <div>
                <label class="block text-xs font-semibold text-neutral-600 mb-1">overlap</label>
                <input
                  v-model.number="form.chunk_overlap" type="number" min="0" max="512"
                  class="w-full text-sm h-9 px-3 rounded-md border border-neutral-200 focus:outline-none focus:ring-1 focus:ring-brand-400"
                />
              </div>
            </div>

            <p v-if="activeFolderId" class="text-[11px] text-neutral-500">
              將建立於資料夾「{{ activeFolderName }}」
            </p>
          </div>
          <div class="px-5 py-3 border-t border-neutral-100 bg-neutral-50 flex items-center justify-end gap-2">
            <button
              @click="showCreate = false"
              class="h-9 px-4 text-sm text-neutral-700 bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50"
            >取消</button>
            <button
              @click="createKB"
              :disabled="!form.name"
              class="h-9 px-4 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg"
            >建立</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- 建立 Folder Modal -->
  <Teleport to="body">
    <div
      v-if="showNewFolder"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-900/40 backdrop-blur-sm"
      @click.self="showNewFolder = false"
    >
      <div class="w-full max-w-sm bg-surface-raised rounded-2xl shadow-2xl overflow-hidden">
        <div class="px-5 py-4 border-b border-neutral-100">
          <h3 class="font-semibold text-sm text-neutral-900">新增資料夾</h3>
        </div>
        <div class="px-5 py-4">
          <input
            v-model="folderForm.name"
            placeholder="例：人事 / 採購 / 法規"
            class="w-full h-9 px-3 text-sm rounded-md border border-neutral-200 focus:outline-none focus:ring-1 focus:ring-brand-400"
            @keyup.enter="createFolder"
          />
          <p v-if="activeFolderId" class="text-[11px] text-neutral-500 mt-2">
            將建立於「{{ activeFolderName }}」之下
          </p>
        </div>
        <div class="px-5 py-3 border-t border-neutral-100 bg-neutral-50 flex justify-end gap-2">
          <button
            @click="showNewFolder = false"
            class="h-9 px-4 text-sm text-neutral-700 bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50"
          >取消</button>
          <button
            :disabled="!folderForm.name.trim()"
            @click="createFolder"
            class="h-9 px-4 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 disabled:opacity-50 rounded-lg"
          >建立</button>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- 批量選擇浮動工具列 -->
  <BatchSelectToolbar :count="batch.count" @clear="batch.clear()">
    <button
      @click="batchDelete"
      class="px-2.5 py-1.5 rounded-lg text-sm text-white/90 hover:bg-white/10 hover:text-white transition"
    >刪除</button>
  </BatchSelectToolbar>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { knowledgeApi, type KbFolder } from '../../api/knowledge'
import { IconClose, IconDelete, IconKnowledge, IconPlus, IconSpinner } from '../../components/icons'
import { useBatchSelect } from '../../composables/useBatchSelect'
import BatchSelectToolbar from '../../components/common/BatchSelectToolbar.vue'
import FolderTree, { type FolderNode } from '../../components/common/FolderTree.vue'
import { useProjectStore } from '../../stores/project'

const kbs = ref<any[]>([])
const folders = ref<KbFolder[]>([])
const loading = ref(true)
const showCreate = ref(false)
const showNewFolder = ref(false)
const form = ref({
  name: '',
  description: '',
  chunk_strategy: 'auto' as 'auto' | 'recursive' | 'markdown' | 'qa',
  chunk_size: 512,
  chunk_overlap: 64,
})

// 切片策略選項（RFC-006）
const CHUNK_STRATEGIES = [
  { value: 'auto',      label: '自動',     desc: '依內容自動偵測（推薦）' },
  { value: 'recursive', label: '遞迴字符', desc: '段→句→字回退；CJK 友好' },
  { value: 'markdown',  label: 'Markdown', desc: '保留 heading 階層脈絡' },
  { value: 'qa',        label: 'Q&A 對',   desc: 'FAQ / 問答格式文件' },
] as const
const folderForm = reactive({ name: '' })

const activeFolderId = ref<string | null>(null)

// ── 批量選擇 ───────────────────────────────────────────────────────────
const batch = useBatchSelect()

// ── D-6：Project 過濾 ─────────────────────────────────────────────────
const projects = useProjectStore()
const activeProject = computed(() => projects.active)

// ── computed ───────────────────────────────────────────────────────────
const filteredKbs = computed(() => {
  let list = kbs.value
  // 先依 Project（D-6），再依 Folder（C-3）
  if (activeProject.value) {
    const ids = new Set(activeProject.value.knowledge_base_ids || [])
    list = list.filter((k) => ids.has(k.id))
  }
  if (activeFolderId.value !== null) {
    list = list.filter((k) => k.folder_id === activeFolderId.value)
  }
  return list
})

const activeFolderName = computed(() => {
  if (activeFolderId.value === null) return '所有知識庫'
  return folders.value.find((f) => f.id === activeFolderId.value)?.name || '資料夾'
})

const folderTreeData = computed<FolderNode[]>(() => {
  // 把 flat folders 轉成 FolderNode tree
  const map: Record<string, FolderNode> = {}
  for (const f of folders.value) {
    map[f.id] = { id: f.id, name: f.name, count: f.kb_count, children: [] }
  }
  const roots: FolderNode[] = []
  for (const f of folders.value) {
    const node = map[f.id]
    if (f.parent_id && map[f.parent_id]) {
      map[f.parent_id].children!.push(node)
    } else {
      roots.push(node)
    }
  }
  return roots
})

// ── helpers ────────────────────────────────────────────────────────────
function statusClass(s: string) {
  return {
    active:   'bg-success-50 text-success-700',
    building: 'bg-warning-50 text-warning-700',
    error:    'bg-danger-50 text-danger-600',
    disabled: 'bg-neutral-100 text-neutral-500',
  }[s] ?? 'bg-neutral-100 text-neutral-500'
}
function statusLabel(s: string) {
  return { active: '正常', building: '建構中', error: '錯誤', disabled: '停用' }[s] ?? s
}

// ── data loading ───────────────────────────────────────────────────────
// 重試 + 永遠 finally 清 loading；避免 503 cold-start 後永遠卡在「載入中…」
async function load() {
  loading.value = true
  try {
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const [kbData, folderData] = await Promise.all([
          knowledgeApi.listBases(),
          knowledgeApi.listFolders().catch(() => []),
        ])
        kbs.value = kbData.data || []
        folders.value = folderData
        return  // 成功就跳出（finally 仍會跑）
      } catch (e: any) {
        const status = e?.response?.status
        if (status && status < 500) throw e
        if (attempt === 2) throw e
        await new Promise(r => setTimeout(r, 800 * Math.pow(2, attempt)))
      }
    }
  } catch (e) {
    console.error('KnowledgeView load failed:', e)
  } finally {
    loading.value = false
  }
}

async function createKB() {
  await knowledgeApi.createBase({
    name: form.value.name,
    description: form.value.description || undefined,
    folder_id: activeFolderId.value,
    chunk_strategy: form.value.chunk_strategy,
    chunk_size: form.value.chunk_size,
    chunk_overlap: form.value.chunk_overlap,
  })
  showCreate.value = false
  form.value = { name: '', description: '', chunk_strategy: 'auto', chunk_size: 512, chunk_overlap: 64 }
  await load()
}

async function deleteKB(id: string) {
  if (!confirm('確定要刪除？其下的文件與向量資料會一併移除。')) return
  await knowledgeApi.deleteBase(id)
  await load()
}

async function batchDelete() {
  const ids = Array.from(batch.selected.value)
  if (ids.length === 0) return
  if (!confirm(`確定要刪除 ${ids.length} 個知識庫？其下的文件與向量資料會一併移除。`)) return
  for (const id of ids) {
    try { await knowledgeApi.deleteBase(id) } catch { /* swallow */ }
  }
  batch.clear()
  await load()
}

async function createFolder() {
  const name = folderForm.name.trim()
  if (!name) return
  try {
    await knowledgeApi.createFolder({ name, parent_id: activeFolderId.value })
    folderForm.name = ''
    showNewFolder.value = false
    await load()
  } catch (e) {
    console.error('create folder failed', e)
  }
}

onMounted(load)
</script>
