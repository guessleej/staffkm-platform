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
            <div class="flex items-center gap-2">
              <button
                v-if="t.is_enabled && (t.kind === 'http' || t.kind === 'mcp')"
                @click="openExec(t)"
                class="text-xs text-brand-600 hover:text-brand-800 transition"
              >試跑</button>
              <button
                @click="onDelete(t.id)"
                class="text-xs text-neutral-400 hover:text-danger-600 transition"
              >刪除</button>
            </div>
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

    <!-- 試跑 modal (D-1) -->
    <Teleport to="body">
      <div
        v-if="execTool"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30"
        @click.self="closeExec"
      >
        <div class="w-full max-w-2xl bg-surface-raised rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[80vh]">
          <div class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between flex-shrink-0">
            <div>
              <h3 class="text-sm font-semibold text-neutral-900">試跑：{{ execTool.name }}</h3>
              <p class="text-[11px] text-neutral-500 mt-0.5">{{ execTool.kind.toUpperCase() }} · 不會修改 workspace 資料</p>
            </div>
            <button @click="closeExec" class="text-neutral-400 hover:text-neutral-700">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>
          <div class="flex-1 overflow-y-auto px-5 py-4 space-y-4">
            <div>
              <label class="block text-xs text-neutral-500 mb-1">輸入 (JSON)</label>
              <textarea
                v-model="execInput"
                rows="6"
                placeholder='{"key": "value"}'
                class="w-full px-3 py-2 text-sm font-mono rounded-md border border-neutral-200 focus:outline-none focus:ring-1 focus:ring-brand-400 resize-y"
              />
              <p v-if="execInputErr" class="text-[11px] text-danger-600 mt-1">{{ execInputErr }}</p>
            </div>

            <div v-if="execResult">
              <label class="block text-xs text-neutral-500 mb-1">結果</label>
              <div
                class="px-3 py-2 rounded-md text-xs border"
                :class="execResult.success
                  ? 'border-success-200 bg-success-50 text-success-800'
                  : 'border-danger-200 bg-danger-50 text-danger-700'"
              >
                <p class="font-semibold">
                  {{ execResult.success ? '成功' : '失敗' }}
                  <span v-if="execResult.status != null" class="font-normal ml-2">HTTP {{ execResult.status }}</span>
                  <span class="font-normal ml-2">· {{ execResult.elapsed_ms }} ms</span>
                </p>
              </div>
              <pre class="mt-2 px-3 py-2 text-[12px] font-mono bg-neutral-50 rounded border border-neutral-200 max-h-64 overflow-auto whitespace-pre-wrap">{{ formattedResult }}</pre>
            </div>
          </div>
          <div class="px-5 py-3 border-t border-neutral-100 bg-neutral-50 flex justify-end gap-2 flex-shrink-0">
            <button @click="closeExec" class="h-9 px-4 text-sm rounded-lg border border-neutral-200">關閉</button>
            <button
              :disabled="execLoading"
              @click="runExec"
              class="h-9 px-4 text-sm rounded-lg bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-40"
            >
              {{ execLoading ? '執行中…' : '執行' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { toolApi, type ToolEntity, type ToolExecResult } from '../../api/extras'
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

// ── 試跑 (D-1) ─────────────────────────────────────────────────────────
const execTool = ref<ToolEntity | null>(null)
const execInput = ref<string>('{}')
const execInputErr = ref<string>('')
const execResult = ref<ToolExecResult | null>(null)
const execLoading = ref(false)

const formattedResult = computed(() => {
  if (!execResult.value) return ''
  const r = execResult.value
  const obj = r.output ?? r.text ?? r.error
  try { return typeof obj === 'string' ? obj : JSON.stringify(obj, null, 2) }
  catch { return String(obj) }
})

function openExec(t: ToolEntity) {
  execTool.value = t
  execInput.value = '{\n  \n}'
  execInputErr.value = ''
  execResult.value = null
}
function closeExec() {
  execTool.value = null
  execResult.value = null
}
async function runExec() {
  if (!execTool.value) return
  let inputs: Record<string, unknown> = {}
  try {
    inputs = JSON.parse(execInput.value || '{}')
    execInputErr.value = ''
  } catch (e: any) {
    execInputErr.value = 'JSON 解析失敗：' + e.message
    return
  }
  execLoading.value = true
  try {
    execResult.value = await toolApi.execute(execTool.value.id, inputs)
  } catch (e: any) {
    execResult.value = {
      success: false, status: null, output: null, text: null,
      elapsed_ms: 0, error: e?.message || String(e),
    }
  } finally {
    execLoading.value = false
  }
}

onMounted(load)
</script>
