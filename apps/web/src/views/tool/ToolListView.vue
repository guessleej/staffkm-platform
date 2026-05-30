<template>
  <div class="flex h-full">
    <EntityFolderSidebar
      kind="tool"
      root-label="所有工具"
      :active-folder-id="activeFolderId"
      @update:active-folder-id="(v) => (activeFolderId = v)"
    />
  <div class="flex-1 flex flex-col overflow-hidden">
    <div class="px-6 py-5 flex-shrink-0">
      <div class="card-hero flex items-center justify-between gap-4">
        <div>
          <h1 class="heading-page heading-accent">工具</h1>
          <p class="text-xs text-fg-tertiary mt-1">共 {{ items.length }} 個</p>
        </div>
        <div class="flex items-center gap-2">
          <button
            @click="showCodeGen = true"
            class="btn btn-warm"
            title="用自然語言描述 → AI 自動生成 Python 程式碼（v2.8）"
          >
            <SIcon name="sparkles" :size="14" />
            AI 生成程式碼
          </button>
          <button
            @click="showCreate = true"
            class="btn btn-primary"
          >
            <IconPlus :size="14" :stroke-width="2.5" />
            建立工具
          </button>
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-auto px-6 pb-6">
      <p v-if="loading" class="text-sm text-fg-tertiary">載入中…</p>
      <EmptyState
        v-else-if="!items.length"
        icon="settings"
        title="尚未建立工具"
        description="Tool 可以是 HTTP API、MCP 連線、shell 指令等"
        action-label="建立第一個工具"
        @action="showCreate = true"
      />
      <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <div
          v-for="(t, idx) in items" :key="t.id"
          class="card-warm fade-up p-5"
          :style="`animation-delay: ${idx * 40}ms`"
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
              <input v-model="draft.name" class="form-input" @keyup.enter="onCreate" />
            </div>
            <div>
              <label class="block text-xs text-neutral-500 mb-1">類型</label>
              <select v-model="draft.kind" class="form-input">
                <option value="http">HTTP API</option>
                <option value="mcp">MCP</option>
                <option value="shell">Shell 指令</option>
                <option value="custom">自訂（Python code）</option>
                <option value="workflow">Workflow（MaxKB v2.8）</option>
              </select>
            </div>
            <!-- Workflow type 才顯示 application picker -->
            <div v-if="draft.kind === 'workflow'">
              <label class="block text-xs text-neutral-500 mb-1">關聯 Application（workflow）</label>
              <select v-model="draft.application_id" class="form-input">
                <option value="">— 請選擇 —</option>
                <option v-for="a in applications" :key="a.id" :value="a.id">{{ a.name }}</option>
              </select>
              <p class="text-[11px] text-neutral-500 mt-1">
                把 workflow application 包成 callable tool，agent 透過 function-calling 自主呼叫。
              </p>
            </div>
            <div>
              <label class="block text-xs text-neutral-500 mb-1">說明</label>
              <textarea v-model="draft.description" rows="2" class="form-textarea" />
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
                class="form-textarea font-mono"
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
    <!-- v2.8：AI 生成程式碼 modal -->
    <Teleport to="body">
      <div
        v-if="showCodeGen"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30"
        @click.self="showCodeGen = false"
      >
        <div class="w-full max-w-3xl bg-surface-raised rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
          <div class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between flex-shrink-0">
            <div>
              <h3 class="text-sm font-semibold text-neutral-900">AI 生成 Tool 程式碼</h3>
              <p class="text-[11px] text-neutral-500 mt-0.5">描述需求 + 輸入/輸出欄位 → LLM 產生 Python `def run(...)`</p>
            </div>
            <button @click="showCodeGen = false" class="text-neutral-400 hover:text-neutral-700">
              <SIcon name="x" :size="16" />
            </button>
          </div>
          <div class="flex-1 overflow-y-auto px-5 py-4 space-y-4">
            <div>
              <label class="block text-xs text-neutral-500 mb-1">描述</label>
              <textarea v-model="codeGen.description" rows="3"
                placeholder="例：呼叫第三方 API 把攝氏轉華氏並回傳"
                class="form-textarea" />
            </div>
            <div>
              <div class="flex items-center justify-between mb-1">
                <label class="text-xs text-neutral-500">輸入欄位</label>
                <button @click="addCodeGenInput" class="text-[11px] text-brand-600 hover:underline">+ 新增</button>
              </div>
              <div v-for="(f, i) in codeGen.inputs" :key="'in-' + i" class="flex gap-2 mb-1">
                <input v-model="f.name" placeholder="name" class="form-input h-9 text-xs flex-1" />
                <select v-model="f.type" class="form-input h-9 text-xs">
                  <option value="string">string</option>
                  <option value="number">number</option>
                  <option value="boolean">boolean</option>
                  <option value="object">object</option>
                  <option value="array">array</option>
                </select>
                <input v-model="f.description" placeholder="描述" class="form-input h-9 text-xs flex-[2]" />
                <button @click="rmCodeGenInput(i)" class="text-neutral-400 hover:text-danger-600 text-xs px-1">×</button>
              </div>
            </div>
            <div>
              <div class="flex items-center justify-between mb-1">
                <label class="text-xs text-neutral-500">輸出欄位</label>
                <button @click="addCodeGenOutput" class="text-[11px] text-brand-600 hover:underline">+ 新增</button>
              </div>
              <div v-for="(f, i) in codeGen.outputs" :key="'out-' + i" class="flex gap-2 mb-1">
                <input v-model="f.name" placeholder="name" class="form-input h-9 text-xs flex-1" />
                <select v-model="f.type" class="form-input h-9 text-xs">
                  <option value="string">string</option>
                  <option value="number">number</option>
                  <option value="boolean">boolean</option>
                  <option value="object">object</option>
                  <option value="array">array</option>
                </select>
                <input v-model="f.description" placeholder="描述" class="form-input h-9 text-xs flex-[2]" />
                <button @click="rmCodeGenOutput(i)" class="text-neutral-400 hover:text-danger-600 text-xs px-1">×</button>
              </div>
            </div>
            <div v-if="generatedCode">
              <label class="block text-xs text-neutral-500 mb-1">生成結果</label>
              <pre class="px-3 py-2 text-[12px] font-mono bg-neutral-50 rounded border border-neutral-200 max-h-72 overflow-auto whitespace-pre-wrap">{{ generatedCode }}</pre>
            </div>
          </div>
          <div class="px-5 py-3 border-t border-neutral-100 bg-neutral-50 flex justify-end gap-2 flex-shrink-0">
            <button @click="showCodeGen = false" class="h-9 px-4 text-sm rounded-lg border border-neutral-200">取消</button>
            <button
              :disabled="codeGenLoading"
              @click="runCodeGen"
              class="h-9 px-4 text-sm rounded-lg bg-brand-50 text-brand-700 hover:bg-brand-100 disabled:opacity-40"
            >{{ codeGenLoading ? '生成中…' : (generatedCode ? '重新生成' : '生成程式碼') }}</button>
            <button
              v-if="generatedCode"
              @click="saveGeneratedTool"
              class="h-9 px-4 text-sm rounded-lg bg-brand-600 text-white hover:bg-brand-700"
            >儲存為 Tool</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { toolApi, type ToolEntity, type ToolExecResult } from '../../api/extras'
import { IconPlus } from '../../components/icons'
import EntityFolderSidebar from '../../components/common/EntityFolderSidebar.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import { useDialog } from '../../composables/useDialog'
import { useToast } from '../../composables/useToast'
import { http } from '../../api'
import { SIcon } from '@staffkm/ui-kit'

const dialog = useDialog()
const toast = useToast()

const allItems = ref<ToolEntity[]>([])
const loading = ref(true)
const showCreate = ref(false)
const draft = reactive({ name: '', description: '', kind: 'http', application_id: '' })
const activeFolderId = ref<string | null>(null)
const applications = ref<Array<{ id: string; name: string }>>([])

async function loadApplications() {
  try {
    const { data } = await http.get('/applications')
    applications.value = (data.data || []).map((a: any) => ({ id: a.id, name: a.name }))
  } catch { /* 非關鍵 */ }
}

const items = computed(() => {
  if (activeFolderId.value === null) return allItems.value
  return allItems.value.filter(t => (t as any).folder_id === activeFolderId.value)
})

async function load() {
  loading.value = true
  try { allItems.value = await toolApi.list() } finally { loading.value = false }
}
async function onCreate() {
  if (!draft.name.trim()) return
  if (draft.kind === 'workflow' && !draft.application_id) {
    toast.error('Workflow tool 必須選擇關聯 application')
    return
  }
  const body: Partial<ToolEntity> = {
    name: draft.name,
    description: draft.description || undefined,
    kind: draft.kind,
    tool_type: draft.kind,
  }
  if (draft.kind === 'workflow') body.application_id = draft.application_id
  await toolApi.create(body)
  draft.name = ''; draft.description = ''; draft.kind = 'http'; draft.application_id = ''
  showCreate.value = false
  await load()
  // v5.12: 新工具落在 root，若正在看某資料夾會被 items 篩掉「看似建了就消失」→ 切回全部
  activeFolderId.value = null
}
async function onDelete(id: string) {
  if (!(await dialog.confirm('確定要刪除此工具？此動作無法復原。', { tone: 'danger', confirmLabel: '刪除' }))) return
  try {
    await toolApi.remove(id)
    toast.success('工具已刪除')
    await load()
  } catch (e: any) {
    toast.error('刪除失敗：' + (e?.message || e))
  }
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

// ── v2.8 AI 生成程式碼 modal ──────────────────────────────────────────
const showCodeGen = ref(false)
const codeGenLoading = ref(false)
const codeGen = reactive({
  description: '',
  inputs: [{ name: '', type: 'string', description: '' }],
  outputs: [{ name: '', type: 'string', description: '' }],
})
const generatedCode = ref<string>('')

function addCodeGenInput()  { codeGen.inputs.push({ name: '', type: 'string', description: '' }) }
function rmCodeGenInput(i: number)  { codeGen.inputs.splice(i, 1) }
function addCodeGenOutput() { codeGen.outputs.push({ name: '', type: 'string', description: '' }) }
function rmCodeGenOutput(i: number) { codeGen.outputs.splice(i, 1) }

async function runCodeGen() {
  if (!codeGen.description.trim()) {
    toast.error('請填寫描述')
    return
  }
  codeGenLoading.value = true
  generatedCode.value = ''
  try {
    const res = await toolApi.generateCode({
      description: codeGen.description,
      inputs:  codeGen.inputs.filter(i => i.name.trim()),
      outputs: codeGen.outputs.filter(o => o.name.trim()),
    })
    generatedCode.value = res.code
    toast.success('已生成程式碼')
  } catch (e: any) {
    toast.error('生成失敗：' + (e?.response?.data?.detail || e?.message || e))
  } finally {
    codeGenLoading.value = false
  }
}

async function saveGeneratedTool() {
  if (!generatedCode.value || !codeGen.description.trim()) return
  const name = codeGen.description.slice(0, 32).replace(/\s+/g, '_')
  await toolApi.create({
    name,
    description: codeGen.description,
    kind: 'custom',
    tool_type: 'custom',
    code: generatedCode.value,
    input_schema:  { fields: codeGen.inputs.filter(i => i.name.trim()) },
    output_schema: { fields: codeGen.outputs.filter(o => o.name.trim()) },
  } as any)
  showCodeGen.value = false
  generatedCode.value = ''
  codeGen.description = ''
  await load()
  toast.success('Tool 已建立')
}

onMounted(async () => {
  await Promise.all([load(), loadApplications()])
})
</script>
