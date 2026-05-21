<template>
  <div class="flex flex-col h-full">
    <!-- 頁首 -->
    <div class="px-6 py-5 flex-shrink-0">
      <div class="card-hero flex items-center justify-between gap-4">
        <div>
          <h1 class="heading-page heading-accent">長期記憶</h1>
          <p class="text-sm text-fg-tertiary mt-1">
            給 AI 助理的長期記憶（user / app / team 三層 scope），重要事實它會記住下次自動帶
          </p>
        </div>
        <button
          @click="openCreate"
          class="btn btn-primary"
        >
          <SIcon name="plus" :size="16" />
          新增記憶
        </button>
      </div>
    </div>

    <!-- 工具列 -->
    <div class="px-6 py-3 border-b border-neutral-100 flex items-center gap-2 flex-shrink-0">
      <!-- scope filter chip -->
      <button v-for="s in scopes" :key="s.value"
              @click="filterScope = s.value as any; load()"
              class="px-3 py-1 text-xs rounded-full border transition flex items-center gap-1"
              :class="filterScope === s.value
                ? 'bg-brand-50 border-brand-300 text-brand-700 font-medium'
                : 'border-neutral-200 text-fg-secondary hover:border-neutral-300'">
        <span>{{ s.emoji }}</span>{{ s.label }}
      </button>
      <div class="flex-1" />
      <!-- search -->
      <div class="relative">
        <SIcon name="search" :size="14" class="absolute left-2.5 top-1/2 -translate-y-1/2 text-fg-tertiary pointer-events-none" />
        <input v-model="searchQ" @keydown.enter="(e) => { if (!(e as any).isComposing) onSearch() }"
               placeholder="搜尋記憶..."
               class="h-9 pl-8 pr-3 w-64 text-sm border border-neutral-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 outline-none" />
      </div>
      <button v-if="searchQ" @click="searchQ=''; load()"
              class="text-xs text-fg-tertiary hover:text-fg px-2">清</button>
    </div>

    <div class="flex-1 overflow-y-auto p-6">
      <div v-if="loading" class="flex justify-center py-20">
        <SSpinner :size="28" />
      </div>

      <EmptyState
        v-else-if="!items.length"
        icon="info"
        :title="searchQ ? '搜尋無結果' : '尚無記憶'"
        :description="searchQ ? '換個關鍵字試試' : '記下重要事實，AI 助理下次會自動帶'"
        :action-label="!searchQ ? '新增第一條記憶' : undefined"
        @action="openCreate"
      />

      <div v-else class="space-y-3">
        <article v-for="(m, idx) in items" :key="m.id"
                 class="card-warm fade-up p-4 group"
                 :style="`animation-delay: ${idx * 40}ms`">
          <div class="flex items-start gap-3">
            <span class="px-2 py-0.5 text-[10px] font-semibold rounded uppercase flex-shrink-0"
                  :class="scopeBadge(m.scope)">
              {{ scopeLabel(m.scope) }}
            </span>
            <div class="min-w-0 flex-1">
              <p class="text-sm text-fg whitespace-pre-wrap">{{ m.content }}</p>
              <div class="mt-2 flex items-center gap-3 text-[11px] text-fg-tertiary flex-wrap">
                <span class="flex items-center gap-1">
                  <SIcon name="alert-circle" :size="11" />
                  重要度 {{ m.importance }}
                </span>
                <span v-if="m.tags.length" class="flex items-center gap-1.5">
                  <span v-for="t in m.tags" :key="t"
                        class="px-1.5 py-0.5 bg-neutral-100 text-fg-secondary rounded">#{{ t }}</span>
                </span>
                <span>命中 {{ m.access_count }} 次</span>
                <span>{{ relTime(m.created_at) }}</span>
              </div>
            </div>
            <button @click="onDelete(m)"
                    class="opacity-0 group-hover:opacity-100 transition px-2 py-1 text-fg-tertiary hover:text-danger-600 hover:bg-danger-50 rounded">
              <SIcon name="trash" :size="14" />
            </button>
          </div>
        </article>
      </div>
    </div>

    <!-- create modal -->
    <Teleport to="body">
      <div v-if="showDialog"
           class="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 backdrop-blur-sm p-4"
           @click.self="showDialog = false">
        <div class="w-full max-w-md bg-surface-raised rounded-2xl shadow-2xl overflow-hidden">
          <div class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between">
            <h3 class="font-semibold text-base text-fg">新增記憶</h3>
            <button @click="showDialog = false" class="p-1 rounded-md text-fg-tertiary hover:text-fg hover:bg-neutral-100">
              <SIcon name="x" :size="16" />
            </button>
          </div>
          <div class="px-5 py-4 space-y-4">
            <div>
              <label class="block text-xs font-semibold text-fg-secondary mb-1.5">
                內容 <span class="text-danger-500">*</span>
              </label>
              <textarea v-model="draft.content" rows="4"
                        placeholder="例：使用者偏好回覆使用條列、引用文件來源"
                        class="form-textarea" />
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-xs font-semibold text-fg-secondary mb-1.5">Scope</label>
                <select v-model="draft.scope"
                        class="form-input">
                  <option value="user">👤 只我自己看得到</option>
                  <option value="app">📱 應用範圍共享</option>
                  <option value="team">👥 整個 workspace</option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-semibold text-fg-secondary mb-1.5">
                  重要度 <span class="text-fg-tertiary font-normal">{{ draft.importance }}</span>
                </label>
                <input v-model.number="draft.importance" type="range" min="1" max="10"
                       class="w-full h-10 accent-brand-600" />
              </div>
            </div>
            <div>
              <label class="block text-xs font-semibold text-fg-secondary mb-1.5">
                標籤 <span class="text-fg-tertiary font-normal">（逗號或空白分隔）</span>
              </label>
              <input v-model="draft.tagsText"
                     placeholder="人事, sop, 重要"
                     class="form-input" />
            </div>
          </div>
          <div class="px-5 py-3 border-t border-neutral-100 bg-neutral-50/40 flex justify-end gap-2">
            <button @click="showDialog = false"
                    class="h-9 px-4 text-sm text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50">取消</button>
            <button @click="onSubmit"
                    :disabled="!draft.content.trim() || submitting"
                    class="h-9 px-4 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 disabled:opacity-50 rounded-lg">
              {{ submitting ? '儲存中…' : '新增' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { SIcon, SSpinner } from '@staffkm/ui-kit'
import { memoryApi, type Memory, type MemoryScope } from '../../api/memory'
import EmptyState from '../../components/common/EmptyState.vue'

const items = ref<Memory[]>([])
const loading = ref(true)
const filterScope = ref<MemoryScope | undefined>(undefined)
const searchQ = ref('')

const showDialog = ref(false)
const submitting = ref(false)
const draft = reactive({
  content: '',
  scope: 'user' as MemoryScope,
  importance: 5,
  tagsText: '',
})

const scopes = [
  { value: undefined, label: '全部', emoji: '🔭' },
  { value: 'user', label: '我的',  emoji: '👤' },
  { value: 'app',  label: '應用',  emoji: '📱' },
  { value: 'team', label: '團隊',  emoji: '👥' },
]

async function load() {
  loading.value = true
  try {
    if (searchQ.value.trim()) {
      items.value = await memoryApi.search({
        query: searchQ.value.trim(),
        scope: filterScope.value,
        top_k: 20,
      })
    } else {
      const r = await memoryApi.list({ scope: filterScope.value, page_size: 100 })
      items.value = r.items
    }
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '載入失敗')
  } finally {
    loading.value = false
  }
}

function onSearch() { load() }

function openCreate() {
  draft.content = ''
  draft.scope = 'user'
  draft.importance = 5
  draft.tagsText = ''
  showDialog.value = true
}

async function onSubmit() {
  submitting.value = true
  try {
    const tags = draft.tagsText
      .split(/[,，\s]+/).map(s => s.trim()).filter(Boolean)
    await memoryApi.create({
      content: draft.content,
      scope: draft.scope,
      importance: draft.importance,
      tags,
    })
    showDialog.value = false
    await load()
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '建立失敗')
  } finally {
    submitting.value = false
  }
}

async function onDelete(m: Memory) {
  if (!confirm(`刪除這條記憶？\n「${m.content.slice(0, 60)}${m.content.length > 60 ? '...' : ''}」`)) return
  await memoryApi.remove(m.id)
  await load()
}

function scopeBadge(s: MemoryScope): string {
  return ({
    user: 'bg-brand-50 text-brand-700',
    app:  'bg-info-50 text-info-700',
    team: 'bg-success-50 text-success-700',
  } as any)[s] || 'bg-neutral-100 text-fg-tertiary'
}
function scopeLabel(s: MemoryScope): string {
  return ({ user: '我的', app: '應用', team: '團隊' } as any)[s] || s
}
function relTime(iso: string): string {
  const t = new Date(iso).getTime()
  if (isNaN(t)) return iso
  const diff = Math.floor((Date.now() - t) / 1000)
  if (diff < 60)    return '剛剛'
  if (diff < 3600)  return `${Math.floor(diff/60)} 分鐘前`
  if (diff < 86400) return `${Math.floor(diff/3600)} 小時前`
  return `${Math.floor(diff/86400)} 天前`
}

onMounted(load)
</script>
