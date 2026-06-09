<template>
  <div class="flex flex-col h-full">
    <!-- 頁首 -->
    <div class="px-6 py-5 flex-shrink-0">
      <div class="card-hero flex items-center justify-between gap-4">
        <div>
          <h1 class="heading-page heading-accent">MCP Servers</h1>
          <p class="text-sm text-fg-tertiary mt-1">
            連接 Model Context Protocol 工具伺服器；註冊後 workflow / agent 都能調用其上工具。
          </p>
        </div>
        <button
          @click="openCreate"
          class="btn btn-primary"
        >
          <SIcon name="plus" :size="16" />
          新增 Server
        </button>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto px-6 pb-6">
      <!-- 教學：如何接一個 MCP Server（可收合）-->
      <div class="mb-4 bg-surface-raised border border-bd rounded-xl overflow-hidden">
        <button
          @click="showHelp = !showHelp"
          class="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-neutral-50 transition"
        >
          <span class="text-sm font-semibold text-fg flex items-center gap-2"><SIcon name="plug" :size="16" class="text-brand-600" /> 如何接一個 MCP Server？</span>
          <span class="text-xs text-fg-tertiary">{{ showHelp ? '收合 ▲' : '展開 ▼' }}</span>
        </button>
        <div v-if="showHelp" class="px-5 pb-5 text-sm text-fg-secondary space-y-3 border-t border-bd">
          <p class="pt-3">
            MCP（Model Context Protocol）是讓 AI 連到外部工具/資料的標準。接上一個 MCP Server，
            就能把它提供的工具<strong class="text-fg">整批自動匯入</strong>給你的 AI 用。
          </p>
          <p class="flex items-start gap-1.5 text-xs bg-brand-50/60 text-brand-800 px-3 py-2 rounded-lg">
            <SIcon name="info" :size="14" class="mt-0.5 shrink-0" />
            <span>跟「<strong>工具</strong>」頁的差別：工具頁是<strong>自己做一個</strong>工具；MCP 是<strong>接別人現成的一整組</strong>工具。</span>
          </p>
          <div>
            <p class="font-medium text-fg mb-1">三步驟</p>
            <ol class="list-decimal list-inside space-y-1">
              <li>點右上 <strong class="text-fg">新增 Server</strong>。</li>
              <li>填：<strong class="text-fg">名稱</strong>、<strong class="text-fg">Transport</strong>（http 或 sse）、<strong class="text-fg">URL</strong>（MCP server 網址，照對方文件填）。</li>
              <li>新增後按卡片上的 <strong class="text-fg">重整</strong> → 自動匯入它的工具；再到 Application/代理人 掛上使用。</li>
            </ol>
          </div>
          <div>
            <p class="font-medium text-fg mb-1">Transport 怎麼選</p>
            <ul class="space-y-1">
              <li class="flex items-start gap-2"><SIcon name="globe" :size="14" class="mt-0.5 shrink-0 text-brand-500" /><span><strong class="text-fg">http</strong> — Streamable HTTP（多數新版 MCP server）</span></li>
              <li class="flex items-start gap-2"><SIcon name="refresh" :size="14" class="mt-0.5 shrink-0 text-brand-500" /><span><strong class="text-fg">sse</strong> — Server-Sent Events（舊版/串流型）</span></li>
            </ul>
          </div>
          <div>
            <p class="font-medium text-fg mb-1">範例</p>
            <pre v-pre class="px-3 py-2 bg-neutral-50 rounded-lg font-mono text-[12px] text-neutral-700 whitespace-pre-wrap border border-neutral-200">名稱：GitHub MCP
Transport：http
URL：https://mcp.example.com/mcp</pre>
          </div>
          <p class="text-xs text-fg-tertiary flex items-start gap-1.5">
            <SIcon name="lightbulb" :size="13" class="mt-0.5 shrink-0 text-amber-500" />
            <span>小提示：連線失敗會在卡片顯示紅色錯誤，先確認 URL 正確、server 在線。匯入的工具也會出現在「工具」清單裡。</span>
          </p>
        </div>
      </div>

      <div v-if="loading" class="flex justify-center py-20">
        <SSpinner :size="28" />
      </div>

      <EmptyState
        v-else-if="!servers.length"
        icon="settings"
        title="尚未連接任何 MCP server"
        description="把外部 MCP 伺服器接進來，自動匯入它上面的工具"
        action-label="新增第一個 Server"
        @action="openCreate"
      />

      <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <div
          v-for="(s, idx) in servers" :key="s.id"
          class="card-warm fade-up p-5"
          :style="`animation-delay: ${idx * 40}ms`"
        >
          <div class="flex items-start gap-3 mb-3">
            <div
              class="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
              :class="s.enabled ? 'bg-success-50 text-success-600' : 'bg-neutral-100 text-fg-tertiary'"
            >
              <SIcon name="settings" :size="20" />
            </div>
            <div class="min-w-0 flex-1">
              <h3 class="font-semibold text-sm text-fg truncate">{{ s.name }}</h3>
              <p class="text-[11px] text-fg-tertiary mt-0.5 font-mono uppercase">{{ s.transport }}</p>
            </div>
            <span
              class="px-2 py-0.5 text-[10px] font-semibold rounded-full flex-shrink-0"
              :class="s.enabled
                ? 'bg-success-50 text-success-700'
                : 'bg-neutral-100 text-fg-tertiary'"
            >{{ s.enabled ? '啟用' : '停用' }}</span>
          </div>

          <p class="text-xs text-fg-secondary line-clamp-2 min-h-[32px] mb-2">
            {{ s.description || '未填寫說明' }}
          </p>

          <p v-if="s.url" class="text-[11px] text-fg-tertiary truncate font-mono mb-2">
            <SIcon name="external-link" :size="10" class="inline-block mr-1" />{{ s.url }}
          </p>

          <div v-if="s.last_error" class="mb-3 flex items-start gap-1.5 px-2 py-1.5 rounded bg-danger-50/60 text-[11px] text-danger-700">
            <SIcon name="alert-circle" :size="12" class="flex-shrink-0 mt-0.5" />
            <span class="truncate">{{ s.last_error }}</span>
          </div>

          <div v-if="s.last_refreshed_at" class="text-[11px] text-fg-tertiary mb-3">
            最後同步：{{ relTime(s.last_refreshed_at) }}
          </div>

          <div class="flex items-center gap-1.5">
            <button
              @click="onRefresh(s)"
              :disabled="busyIds.has(s.id)"
              class="flex-1 text-center text-xs font-medium text-brand-700 bg-brand-50 hover:bg-brand-100 py-1.5 rounded-md transition disabled:opacity-50 flex items-center justify-center gap-1"
            >
              <SIcon name="refresh" :size="12" :class="busyIds.has(s.id) ? 'animate-spin' : ''" />
              重抓 tools
            </button>
            <button
              @click="openTools(s)"
              class="flex-1 text-center text-xs font-medium text-fg-secondary bg-neutral-100 hover:bg-neutral-200 py-1.5 rounded-md transition"
            >看 tools</button>
            <button
              @click="toggleEnabled(s)"
              class="px-2.5 text-fg-tertiary hover:text-fg hover:bg-neutral-100 rounded-md py-1.5 transition"
              :title="s.enabled ? '停用' : '啟用'"
            >
              <SIcon :name="s.enabled ? 'pause' : 'play'" :size="14" />
            </button>
            <button
              @click="openEdit(s)"
              class="px-2.5 text-fg-tertiary hover:text-brand-600 hover:bg-brand-50 rounded-md py-1.5 transition"
              title="編輯"
            >
              <SIcon name="edit" :size="14" />
            </button>
            <button
              @click="confirmDelete(s)"
              class="px-2.5 text-fg-tertiary hover:text-danger-600 hover:bg-danger-50 rounded-md py-1.5 transition"
              title="刪除"
            >
              <SIcon name="trash" :size="14" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 建立 / 編輯 server modal -->
    <Teleport to="body">
      <div
        v-if="showDialog"
        class="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 backdrop-blur-sm p-4"
        @click.self="showDialog = false"
      >
        <div class="w-full max-w-md bg-surface-raised rounded-2xl shadow-2xl overflow-hidden">
          <div class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between">
            <h3 class="font-semibold text-base text-fg">
              {{ editingId ? '編輯 MCP Server' : '新增 MCP Server' }}
            </h3>
            <button @click="showDialog = false" class="p-1 rounded-md text-fg-tertiary hover:text-fg hover:bg-neutral-100">
              <SIcon name="x" :size="16" />
            </button>
          </div>
          <div class="px-5 py-4 space-y-4">
            <div>
              <label class="block text-xs font-semibold text-fg-secondary mb-1.5">名稱 <span class="text-danger-500">*</span></label>
              <input
                v-model="draft.name"
                placeholder="例：本地 GitHub MCP"
                class="form-input"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold text-fg-secondary mb-1.5">說明</label>
              <textarea
                v-model="draft.description"
                rows="2"
                placeholder="這個 server 提供什麼工具？"
                class="form-textarea"
              />
            </div>
            <div class="grid grid-cols-3 gap-2">
              <div class="col-span-1">
                <label class="block text-xs font-semibold text-fg-secondary mb-1.5">Transport</label>
                <select
                  v-model="draft.transport"
                  class="form-input"
                >
                  <option value="http">http</option>
                  <option value="sse">sse</option>
                </select>
              </div>
              <div class="col-span-2">
                <label class="block text-xs font-semibold text-fg-secondary mb-1.5">URL <span class="text-danger-500">*</span></label>
                <input
                  v-model="draft.url"
                  type="url"
                  placeholder="https://mcp.example.com/mcp"
                  class="form-input font-mono"
                />
              </div>
            </div>
            <label class="flex items-center gap-2 text-sm text-fg-secondary cursor-pointer">
              <input v-model="draft.enabled" type="checkbox" class="w-4 h-4 rounded text-brand-600">
              <span>啟用此 server</span>
            </label>
          </div>
          <div class="px-5 py-3 border-t border-neutral-100 bg-neutral-50/40 flex items-center justify-end gap-2">
            <button
              @click="showDialog = false"
              class="h-9 px-4 text-sm text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50"
            >取消</button>
            <button
              @click="onSubmit"
              :disabled="!draft.name.trim() || !draft.url?.trim() || submitting"
              class="h-9 px-4 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 disabled:opacity-50 rounded-lg"
            >
              {{ submitting ? '儲存中…' : (editingId ? '儲存' : '新增') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- tools drawer -->
    <Teleport to="body">
      <Transition
        enter-active-class="transition-transform duration-300 ease-out"
        enter-from-class="translate-x-full"
        leave-active-class="transition-transform duration-200 ease-in"
        leave-to-class="translate-x-full"
      >
        <aside
          v-if="toolsOpen"
          class="fixed top-0 right-0 h-full w-[480px] z-50 bg-surface-raised border-l border-neutral-200 flex flex-col shadow-2xl"
        >
          <header class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between flex-shrink-0">
            <div class="min-w-0">
              <p class="text-[10px] uppercase tracking-widest text-fg-tertiary">TOOLS</p>
              <h3 class="font-semibold text-sm text-fg truncate">{{ toolsTarget?.name || 'Server' }}</h3>
            </div>
            <button @click="toolsOpen = false" class="p-1.5 rounded-md text-fg-tertiary hover:text-fg hover:bg-neutral-100">
              <SIcon name="x" :size="18" />
            </button>
          </header>
          <div class="flex-1 overflow-y-auto px-5 py-4">
            <div v-if="toolsLoading" class="flex justify-center py-10">
              <SSpinner :size="24" />
            </div>
            <p v-else-if="!toolsList.length" class="text-sm text-fg-tertiary text-center py-10">
              這個 server 還沒快取 tools，<br>請先回上頁按「重抓 tools」
            </p>
            <ul v-else class="space-y-2">
              <li v-for="t in toolsList" :key="t.id" class="border border-neutral-200 rounded-lg p-3">
                <div class="flex items-start gap-2">
                  <SIcon name="settings" :size="14" class="text-fg-tertiary mt-0.5 flex-shrink-0" />
                  <div class="min-w-0 flex-1">
                    <p class="font-mono text-sm text-fg break-all">{{ t.name }}</p>
                    <p v-if="t.description" class="text-xs text-fg-secondary mt-1">{{ t.description }}</p>
                    <details v-if="hasSchema(t)" class="mt-2">
                      <summary class="text-[11px] text-fg-tertiary cursor-pointer hover:text-fg">輸入 schema</summary>
                      <pre class="mt-1 text-[11px] bg-neutral-50 p-2 rounded font-mono text-fg-secondary overflow-x-auto">{{ JSON.stringify(t.input_schema, null, 2) }}</pre>
                    </details>
                  </div>
                </div>
              </li>
            </ul>
          </div>
        </aside>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { SIcon, SSpinner } from '@staffkm/ui-kit'
import { mcpApi, type McpServer, type McpTool } from '../../api/mcp'
import EmptyState from '../../components/common/EmptyState.vue'

const servers = ref<McpServer[]>([])
const loading = ref(true)
const showHelp = ref(true)   // 教學卡：預設展開、可收合
const busyIds = ref(new Set<string>())

const showDialog = ref(false)
const editingId = ref<string | null>(null)
const submitting = ref(false)
const draft = reactive({
  name: '',
  description: '',
  transport: 'http' as 'http' | 'sse',
  url: '',
  enabled: true,
})

const toolsOpen = ref(false)
const toolsTarget = ref<McpServer | null>(null)
const toolsLoading = ref(false)
const toolsList = ref<McpTool[]>([])

async function load() {
  loading.value = true
  try { servers.value = await mcpApi.list() } finally { loading.value = false }
}

function resetDraft() {
  draft.name = ''
  draft.description = ''
  draft.transport = 'http'
  draft.url = ''
  draft.enabled = true
  editingId.value = null
}

function openCreate() { resetDraft(); showDialog.value = true }
function openEdit(s: McpServer) {
  editingId.value = s.id
  draft.name = s.name
  draft.description = s.description || ''
  draft.transport = (s.transport as 'http' | 'sse') || 'http'
  draft.url = s.url || ''
  draft.enabled = s.enabled
  showDialog.value = true
}

async function onSubmit() {
  submitting.value = true
  try {
    if (editingId.value) {
      await mcpApi.update(editingId.value, {
        name: draft.name, description: draft.description || null,
        url: draft.url, enabled: draft.enabled,
      })
    } else {
      await mcpApi.create({
        name: draft.name, description: draft.description || undefined,
        transport: draft.transport, url: draft.url, enabled: draft.enabled,
      })
    }
    showDialog.value = false
    await load()
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '失敗')
  } finally {
    submitting.value = false
  }
}

async function confirmDelete(s: McpServer) {
  if (!confirm(`刪除 MCP server「${s.name}」？相關 tools 快取會一併清空。`)) return
  await mcpApi.remove(s.id)
  await load()
}

async function toggleEnabled(s: McpServer) {
  await mcpApi.update(s.id, { enabled: !s.enabled })
  await load()
}

async function onRefresh(s: McpServer) {
  if (busyIds.value.has(s.id)) return
  busyIds.value.add(s.id)
  try {
    const r = await mcpApi.refresh(s.id)
    await load()
    alert(`已重抓 ${r.count} 個 tools`)
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '重抓失敗')
    await load()
  } finally {
    busyIds.value.delete(s.id)
  }
}

async function openTools(s: McpServer) {
  toolsTarget.value = s
  toolsOpen.value = true
  toolsLoading.value = true
  try { toolsList.value = await mcpApi.listTools(s.id) }
  finally { toolsLoading.value = false }
}

function hasSchema(t: McpTool): boolean {
  return t.input_schema && Object.keys(t.input_schema).length > 0
}

function relTime(iso: string): string {
  const t = new Date(iso).getTime()
  if (isNaN(t)) return iso
  const diff = Math.floor((Date.now() - t) / 1000)
  if (diff < 60)   return `${diff} 秒前`
  if (diff < 3600) return `${Math.floor(diff / 60)} 分鐘前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小時前`
  return `${Math.floor(diff / 86400)} 天前`
}

onMounted(load)
</script>
