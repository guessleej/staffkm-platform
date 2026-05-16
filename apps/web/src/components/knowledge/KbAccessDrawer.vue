<template>
  <Teleport to="body">
    <transition
      enter-active-class="transition-opacity duration-150"
      enter-from-class="opacity-0"
      leave-active-class="transition-opacity duration-100"
      leave-to-class="opacity-0"
    >
      <div v-if="open" class="fixed inset-0 z-[300] bg-black/40" @click.self="close" @keydown.esc="close">
        <transition
          enter-active-class="transition-transform duration-200"
          enter-from-class="translate-x-full"
          enter-to-class="translate-x-0"
          leave-active-class="transition-transform duration-150"
          leave-to-class="translate-x-full"
          appear
        >
          <aside class="absolute right-0 top-0 bottom-0 w-[480px] bg-surface-raised shadow-2xl flex flex-col"
                 role="dialog" aria-modal="true">
            <header class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between">
              <div>
                <h3 class="text-sm font-semibold text-neutral-900">資源授權 · {{ kbName }}</h3>
                <p class="text-[11px] text-neutral-500 mt-0.5">{{ tab === 'grants' ? '管理可存取此知識庫的對象' : '哪些 application 引用了此 KB' }}</p>
              </div>
              <button @click="close" class="text-neutral-400 hover:text-neutral-700" aria-label="關閉">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </header>

            <div class="px-5 pt-3 border-b border-neutral-100 flex gap-1">
              <button @click="tab='grants'"
                      :class="['px-3 py-1.5 text-xs rounded-md',
                               tab==='grants' ? 'bg-brand-50 text-brand-700' : 'text-neutral-500 hover:bg-neutral-50']">授權</button>
              <button @click="tab='related'; loadRelated()"
                      :class="['px-3 py-1.5 text-xs rounded-md',
                               tab==='related' ? 'bg-brand-50 text-brand-700' : 'text-neutral-500 hover:bg-neutral-50']">關聯資源</button>
            </div>

            <!-- Tab: 授權 -->
            <div v-if="tab==='grants'" class="flex-1 overflow-y-auto p-5 space-y-4">
              <!-- 新增 -->
              <section class="bg-neutral-50 border border-neutral-100 rounded-xl p-3 space-y-2">
                <h4 class="text-xs font-semibold text-neutral-700">新增授權</h4>
                <div class="grid grid-cols-3 gap-2">
                  <select v-model="draft.principal_type" class="h-8 text-xs px-2 border border-neutral-200 rounded-md">
                    <option value="user">使用者</option>
                    <option value="role">角色</option>
                    <option value="workspace">整個工作區</option>
                  </select>
                  <input v-if="draft.principal_type !== 'workspace'"
                         v-model="draft.principal_id"
                         class="h-8 text-xs px-2 border border-neutral-200 rounded-md"
                         :placeholder="draft.principal_type === 'role' ? 'owner / admin / editor / viewer' : 'user UUID'"/>
                  <input v-else value="此工作區所有成員" disabled
                         class="h-8 text-xs px-2 border border-neutral-200 rounded-md bg-neutral-100"/>
                  <select v-model="draft.access" class="h-8 text-xs px-2 border border-neutral-200 rounded-md">
                    <option value="read">read</option>
                    <option value="edit">edit</option>
                    <option value="manage">manage</option>
                  </select>
                </div>
                <button @click="add" :disabled="!canAdd || busy"
                        class="w-full h-8 text-xs bg-brand-600 text-white rounded-md hover:bg-brand-700 disabled:opacity-40">
                  {{ busy ? '處理中…' : '新增' }}
                </button>
              </section>

              <!-- 列表 -->
              <section>
                <h4 class="text-xs font-semibold text-neutral-700 mb-2">已授權對象（{{ grants.length }}）</h4>
                <p v-if="!grants.length" class="text-xs text-neutral-400 py-6 text-center">
                  尚無授權 — 預設為 workspace 全體可讀。一旦新增任一筆，將切換為白名單模式。
                </p>
                <ul v-else class="space-y-1">
                  <li v-for="g in grants" :key="g.id"
                      class="flex items-center gap-2 p-2 border border-neutral-100 rounded-lg">
                    <span class="text-[10px] px-1.5 py-0.5 rounded bg-neutral-100 text-neutral-600 uppercase tracking-wider">{{ g.principal_type }}</span>
                    <span class="flex-1 text-xs font-mono truncate text-neutral-700">
                      {{ g.principal_type === 'workspace' ? '*' : g.principal_id }}
                    </span>
                    <span class="text-[10px] px-1.5 py-0.5 rounded bg-brand-50 text-brand-700">{{ g.access }}</span>
                    <button @click="remove(g.id)" class="text-neutral-300 hover:text-danger-600">
                      <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                      </svg>
                    </button>
                  </li>
                </ul>
              </section>
            </div>

            <!-- Tab: 關聯資源 -->
            <div v-if="tab==='related'" class="flex-1 overflow-y-auto p-5 space-y-3">
              <p v-if="relatedLoading" class="text-xs text-neutral-400 text-center py-6">載入中…</p>
              <p v-else-if="!related.applications.length" class="text-xs text-neutral-400 text-center py-6">
                目前沒有 application 引用此 KB。
              </p>
              <ul v-else class="space-y-1">
                <li v-for="app in related.applications" :key="app.id"
                    class="flex items-center gap-2 p-2 border border-neutral-100 rounded-lg">
                  <span class="text-[10px] px-1.5 py-0.5 rounded bg-info-50 text-info-700 uppercase">{{ app.type }}</span>
                  <span class="flex-1 text-xs text-neutral-800 truncate">{{ app.name }}</span>
                  <span class="text-[10px] text-neutral-400 font-mono">{{ app.status }}</span>
                </li>
              </ul>
            </div>
          </aside>
        </transition>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { knowledgeApi } from '../../api/knowledge'

const props = defineProps<{ open: boolean; kbId: string; kbName: string }>()
const emit  = defineEmits<{ (e: 'update:open', v: boolean): void }>()

const tab = ref<'grants' | 'related'>('grants')
const grants = ref<any[]>([])
const related = ref<{ applications: any[] }>({ applications: [] })
const relatedLoading = ref(false)
const busy = ref(false)

const draft = reactive<{ principal_type: 'user'|'role'|'workspace'; principal_id: string; access: 'read'|'edit'|'manage' }>({
  principal_type: 'user', principal_id: '', access: 'read',
})

function close() { emit('update:open', false) }

const canAdd = computedCanAdd()
function computedCanAdd() {
  // 用普通 ref + 監聽（避免 import 多一個 computed）
  return ref(true)
}

watch(() => props.open, async (v) => {
  if (!v) return
  tab.value = 'grants'
  await load()
})

async function load() {
  try { grants.value = await knowledgeApi.listKbGrants(props.kbId) }
  catch (e: any) { alert('讀取授權失敗：' + (e?.message || e)) }
}
async function loadRelated() {
  if (related.value.applications.length) return
  relatedLoading.value = true
  try { related.value = await knowledgeApi.kbRelatedResources(props.kbId) }
  catch (e: any) { alert('讀取關聯資源失敗：' + (e?.message || e)) }
  finally { relatedLoading.value = false }
}
async function add() {
  if (draft.principal_type !== 'workspace' && !draft.principal_id.trim()) {
    alert('請填 principal_id')
    return
  }
  busy.value = true
  try {
    await knowledgeApi.addKbGrant(props.kbId, {
      principal_type: draft.principal_type,
      principal_id:   draft.principal_type === 'workspace' ? '*' : draft.principal_id.trim(),
      access:         draft.access,
    })
    draft.principal_id = ''
    await load()
  } catch (e: any) {
    alert('新增失敗：' + (e?.response?.data?.detail || e?.message))
  } finally { busy.value = false }
}
async function remove(gid: string) {
  if (!confirm('確定要移除此授權？')) return
  try { await knowledgeApi.deleteKbGrant(props.kbId, gid); await load() }
  catch (e: any) { alert('刪除失敗：' + (e?.message || e)) }
}
</script>
