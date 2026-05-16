<template>
  <div class="flex flex-col h-full">
    <div class="px-6 py-5 border-b border-neutral-200 bg-surface-raised flex items-center justify-between flex-shrink-0">
      <div>
        <h1 class="text-lg font-semibold text-neutral-900">工具</h1>
        <p class="text-xs text-neutral-500 mt-0.5">共 {{ items.length }} 個</p>
      </div>
      <button
        @click="showCreate = true"
        class="inline-flex items-center gap-1.5 h-9 px-4 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-lg transition-colors shadow-sm"
      >
        <IconPlus :size="14" :stroke-width="2.5" />
        建立工具
      </button>
    </div>

    <div class="flex-1 overflow-auto p-6">
      <p v-if="loading" class="text-sm text-neutral-400">載入中…</p>
      <div v-else-if="!items.length" class="text-center py-20 text-sm text-neutral-500">
        尚未建立工具。Tool 可以是 HTTP API、MCP 連線、shell 指令等。
      </div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <div
          v-for="t in items" :key="t.id"
          class="bg-surface-raised rounded-xl border border-neutral-200 hover:border-brand-300 hover:shadow-md transition-all p-5"
        >
          <div class="flex items-center justify-between mb-2">
            <h3 class="font-semibold text-sm text-neutral-900 truncate">{{ t.name }}</h3>
            <span class="text-[10px] uppercase tracking-widest text-neutral-400">{{ t.kind }}</span>
          </div>
          <p class="text-xs text-neutral-500 line-clamp-2 min-h-[2rem]">
            {{ t.description || '尚未填寫說明' }}
          </p>
          <div class="mt-3 flex items-center justify-between">
            <span
              class="text-[11px] px-2 py-0.5 rounded-full"
              :class="t.is_enabled ? 'bg-success-50 text-success-700' : 'bg-neutral-100 text-neutral-500'"
            >{{ t.is_enabled ? '啟用' : '停用' }}</span>
            <button
              @click="onDelete(t.id)"
              class="text-xs text-neutral-400 hover:text-danger-600 transition"
            >刪除</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 建立 modal -->
    <Teleport to="body">
      <div
        v-if="showCreate"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30"
        @click.self="showCreate = false"
      >
        <div class="w-full max-w-md bg-surface-raised rounded-2xl shadow-2xl overflow-hidden">
          <div class="px-5 py-4 border-b border-neutral-100">
            <h3 class="text-sm font-semibold text-neutral-900">建立工具</h3>
          </div>
          <div class="px-5 py-4 space-y-3">
            <div>
              <label class="block text-xs text-neutral-500 mb-1">名稱</label>
              <input v-model="draft.name" class="w-full h-9 px-3 text-sm rounded-md border border-neutral-200 focus:outline-none focus:ring-1 focus:ring-brand-400" />
            </div>
            <div>
              <label class="block text-xs text-neutral-500 mb-1">類型</label>
              <select v-model="draft.kind" class="w-full h-9 px-2 text-sm rounded-md border border-neutral-200">
                <option value="http">HTTP API</option>
                <option value="mcp">MCP</option>
                <option value="shell">Shell 指令</option>
                <option value="custom">自訂</option>
              </select>
            </div>
            <div>
              <label class="block text-xs text-neutral-500 mb-1">說明</label>
              <textarea v-model="draft.description" rows="2" class="w-full px-3 py-2 text-sm rounded-md border border-neutral-200 resize-none focus:outline-none focus:ring-1 focus:ring-brand-400" />
            </div>
          </div>
          <div class="px-5 py-3 border-t border-neutral-100 bg-neutral-50 flex justify-end gap-2">
            <button @click="showCreate = false" class="h-9 px-4 text-sm rounded-lg border border-neutral-200">取消</button>
            <button :disabled="!draft.name.trim()" @click="onCreate" class="h-9 px-4 text-sm rounded-lg bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-40">建立</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { toolApi, type ToolEntity } from '../../api/extras'
import { IconPlus } from '../../components/icons'

const items = ref<ToolEntity[]>([])
const loading = ref(true)
const showCreate = ref(false)
const draft = reactive({ name: '', description: '', kind: 'http' })

async function load() {
  loading.value = true
  try { items.value = await toolApi.list() } finally { loading.value = false }
}
async function onCreate() {
  if (!draft.name.trim()) return
  await toolApi.create({ name: draft.name, description: draft.description || undefined, kind: draft.kind })
  draft.name = ''; draft.description = ''; draft.kind = 'http'
  showCreate.value = false
  await load()
}
async function onDelete(id: string) {
  if (!confirm('確定要刪除此工具？')) return
  await toolApi.remove(id); await load()
}

onMounted(load)
</script>
