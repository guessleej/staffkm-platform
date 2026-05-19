<template>
  <div class="flex flex-col h-full">
    <!-- 頁首 -->
    <div class="px-6 py-5 flex-shrink-0">
      <div class="card-hero flex items-center justify-between gap-4">
        <div>
          <h1 class="heading-page heading-accent">排程觸發</h1>
          <p class="text-sm text-fg-tertiary mt-1">
            設定 interval / cron / webhook 觸發應用，自動執行任務並寫紀錄
          </p>
        </div>
        <button
          @click="openCreate"
          :disabled="!apps.length"
          class="btn btn-primary"
          :title="apps.length ? '' : '請先建立至少一個應用'"
        >
          <SIcon name="plus" :size="16" />
          新增 Trigger
        </button>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto px-6 pb-6">
      <div v-if="loading" class="flex justify-center py-20">
        <SSpinner :size="28" />
      </div>

      <EmptyState
        v-else-if="!triggers.length"
        icon="refresh"
        title="尚未建立任何 Trigger"
        :description="apps.length ? '幫應用排個 interval、cron 表達式、或開 webhook 端點' : '請先到「應用」建立至少一個應用'"
        :action-label="apps.length ? '新增第一個 Trigger' : undefined"
        @action="openCreate"
      />

      <!-- 列表（table） -->
      <div v-else class="card-warm overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="bg-surface-sunken text-xs uppercase tracking-wider text-fg-tertiary text-left">
            <th class="px-4 py-3 font-semibold">名稱 / 應用</th>
            <th class="px-4 py-3 font-semibold">類型</th>
            <th class="px-4 py-3 font-semibold">設定</th>
            <th class="px-4 py-3 font-semibold">下次 / 上次觸發</th>
            <th class="px-4 py-3 font-semibold">狀態</th>
            <th class="px-4 py-3 font-semibold text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in triggers" :key="t.id"
              class="border-t border-neutral-100 hover:bg-neutral-50/40 transition">
            <td class="px-4 py-3">
              <div class="font-medium text-fg">{{ t.name }}</div>
              <div class="text-[11px] text-fg-tertiary mt-0.5 truncate max-w-[200px]">
                {{ appName(t.application_id) }}
              </div>
            </td>
            <td class="px-4 py-3">
              <span class="px-2 py-0.5 text-[10px] font-semibold rounded uppercase"
                    :class="kindBadge(t.kind)">{{ t.kind }}</span>
            </td>
            <td class="px-4 py-3 font-mono text-xs text-fg-secondary">
              <span v-if="t.kind === 'interval'">每 {{ t.interval_sec }}s</span>
              <span v-else-if="t.kind === 'cron'">{{ t.cron_expr }}</span>
              <span v-else class="text-fg-tertiary">webhook</span>
            </td>
            <td class="px-4 py-3 text-xs text-fg-secondary">
              <div v-if="t.next_fire_at" class="flex items-center gap-1">
                <SIcon name="play" :size="10" class="text-fg-tertiary" />
                {{ relTime(t.next_fire_at, true) }}
              </div>
              <div v-if="t.last_fired_at" class="flex items-center gap-1 text-fg-tertiary mt-0.5">
                <SIcon name="check" :size="10" />
                {{ relTime(t.last_fired_at) }}
              </div>
            </td>
            <td class="px-4 py-3">
              <span class="px-2 py-0.5 text-[10px] font-semibold rounded-full"
                    :class="statusBadge(t)">{{ statusLabel(t) }}</span>
              <div v-if="t.last_error" class="text-[10px] text-danger-600 mt-1 truncate max-w-[180px]" :title="t.last_error">
                {{ t.last_error }}
              </div>
            </td>
            <td class="px-4 py-3 text-right">
              <div class="inline-flex items-center gap-1">
                <button @click="openRuns(t)"
                        class="px-2 py-1 text-xs text-fg-secondary hover:text-brand-600 hover:bg-brand-50 rounded transition"
                        title="看執行紀錄">
                  <SIcon name="file-text" :size="14" />
                </button>
                <button @click="toggleEnabled(t)"
                        class="px-2 py-1 text-xs text-fg-tertiary hover:text-fg hover:bg-neutral-100 rounded transition"
                        :title="t.enabled ? '停用' : '啟用'">
                  <SIcon :name="t.enabled ? 'pause' : 'play'" :size="14" />
                </button>
                <button @click="openEdit(t)"
                        class="px-2 py-1 text-xs text-fg-tertiary hover:text-brand-600 hover:bg-brand-50 rounded transition"
                        title="編輯">
                  <SIcon name="edit" :size="14" />
                </button>
                <button @click="confirmDelete(t)"
                        class="px-2 py-1 text-xs text-fg-tertiary hover:text-danger-600 hover:bg-danger-50 rounded transition"
                        title="刪除">
                  <SIcon name="trash" :size="14" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      </div>
    </div>

    <!-- 建立 / 編輯 modal -->
    <Teleport to="body">
      <div v-if="showDialog"
           class="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 backdrop-blur-sm p-4"
           @click.self="showDialog = false">
        <div class="w-full max-w-md bg-surface-raised rounded-2xl shadow-2xl overflow-hidden">
          <div class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between">
            <h3 class="font-semibold text-base text-fg">
              {{ editingId ? '編輯 Trigger' : '新增 Trigger' }}
            </h3>
            <button @click="showDialog = false" class="p-1 rounded-md text-fg-tertiary hover:text-fg hover:bg-neutral-100">
              <SIcon name="x" :size="16" />
            </button>
          </div>
          <div class="px-5 py-4 space-y-4">
            <div>
              <label class="block text-xs font-semibold text-fg-secondary mb-1.5">
                名稱 <span class="text-danger-500">*</span>
              </label>
              <input v-model="draft.name" placeholder="例：每日早上 9:00 報告"
                     class="w-full h-10 px-3 text-sm rounded-lg border border-neutral-200 focus:border-brand-500 focus:ring-2 focus:ring-brand-100 outline-none" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-fg-secondary mb-1.5">
                目標應用 <span class="text-danger-500">*</span>
              </label>
              <select v-model="draft.application_id"
                      :disabled="!!editingId"
                      class="w-full h-10 px-2 text-sm rounded-lg border border-neutral-200 focus:border-brand-500 focus:ring-2 focus:ring-brand-100 outline-none bg-surface-raised disabled:opacity-60">
                <option value="">-- 選一個 --</option>
                <option v-for="a in apps" :key="a.id" :value="a.id">{{ a.name }}</option>
              </select>
            </div>

            <div>
              <label class="block text-xs font-semibold text-fg-secondary mb-1.5">類型</label>
              <div class="grid grid-cols-3 gap-2">
                <button v-for="k in (['interval','cron','webhook'] as const)" :key="k"
                        type="button"
                        :disabled="!!editingId"
                        @click="draft.kind = k"
                        class="px-3 py-2 text-xs rounded-lg border transition disabled:opacity-50"
                        :class="draft.kind === k
                          ? 'border-brand-400 bg-brand-50 text-brand-700 font-semibold'
                          : 'border-neutral-200 text-fg-secondary hover:border-brand-300'">
                  {{ k === 'interval' ? '⏱ Interval' : k === 'cron' ? '📅 Cron' : '🪝 Webhook' }}
                </button>
              </div>
            </div>

            <div v-if="draft.kind === 'interval'">
              <label class="block text-xs font-semibold text-fg-secondary mb-1.5">
                Interval (秒) <span class="text-danger-500">*</span>
              </label>
              <input v-model.number="draft.interval_sec" type="number" min="10"
                     placeholder="3600 = 每小時"
                     class="w-full h-10 px-3 text-sm rounded-lg border border-neutral-200 focus:border-brand-500 focus:ring-2 focus:ring-brand-100 outline-none font-mono" />
              <p class="text-[11px] text-fg-tertiary mt-1">最低 10 秒；常用值：60 / 300 / 3600 / 86400</p>
            </div>
            <div v-else-if="draft.kind === 'cron'">
              <label class="block text-xs font-semibold text-fg-secondary mb-1.5">
                Cron 表達式 <span class="text-danger-500">*</span>
              </label>
              <input v-model="draft.cron_expr" placeholder="0 9 * * *  (每日 9:00)"
                     class="w-full h-10 px-3 text-sm rounded-lg border border-neutral-200 focus:border-brand-500 focus:ring-2 focus:ring-brand-100 outline-none font-mono" />
              <p class="text-[11px] text-fg-tertiary mt-1">標準 5-field cron（分 時 日 月 周）</p>
            </div>
            <div v-else>
              <p class="text-xs text-fg-secondary px-3 py-2 bg-info-50 border border-info-200 rounded-lg">
                webhook 模式建立後將自動分配 endpoint，可從詳情頁複製 URL 給外部系統呼叫
              </p>
            </div>

            <div>
              <label class="block text-xs font-semibold text-fg-secondary mb-1.5">
                輸入模板
                <span class="text-fg-tertiary font-normal">（每次觸發傳給應用的訊息）</span>
              </label>
              <textarea v-model="draft.input_template" rows="2"
                        placeholder="例：請總結今日新進文件"
                        class="w-full px-3 py-2 text-sm rounded-lg border border-neutral-200 focus:border-brand-500 focus:ring-2 focus:ring-brand-100 outline-none resize-none" />
            </div>

            <label class="flex items-center gap-2 text-sm text-fg-secondary cursor-pointer">
              <input v-model="draft.enabled" type="checkbox" class="w-4 h-4 rounded text-brand-600">
              <span>啟用此 trigger</span>
            </label>
          </div>
          <div class="px-5 py-3 border-t border-neutral-100 bg-neutral-50/40 flex items-center justify-end gap-2">
            <button @click="showDialog = false"
                    class="h-9 px-4 text-sm text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50">取消</button>
            <button @click="onSubmit"
                    :disabled="!canSubmit || submitting"
                    class="h-9 px-4 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 disabled:opacity-50 rounded-lg">
              {{ submitting ? '儲存中…' : (editingId ? '儲存' : '新增') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- runs drawer -->
    <Teleport to="body">
      <Transition
        enter-active-class="transition-transform duration-300 ease-out"
        enter-from-class="translate-x-full"
        leave-active-class="transition-transform duration-200 ease-in"
        leave-to-class="translate-x-full"
      >
        <aside v-if="runsOpen"
               class="fixed top-0 right-0 h-full w-[520px] z-50 bg-surface-raised border-l border-neutral-200 flex flex-col shadow-2xl">
          <header class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between flex-shrink-0">
            <div class="min-w-0">
              <p class="text-[10px] uppercase tracking-widest text-fg-tertiary">RUNS · 最多 100 筆</p>
              <h3 class="font-semibold text-sm text-fg truncate">{{ runsTarget?.name || 'Trigger' }}</h3>
            </div>
            <button @click="runsOpen = false" class="p-1.5 rounded-md text-fg-tertiary hover:text-fg hover:bg-neutral-100">
              <SIcon name="x" :size="18" />
            </button>
          </header>
          <div class="flex-1 overflow-y-auto px-5 py-4">
            <div v-if="runsLoading" class="flex justify-center py-10">
              <SSpinner :size="24" />
            </div>
            <p v-else-if="!runs.length" class="text-sm text-fg-tertiary text-center py-10">
              這個 trigger 還沒跑過
            </p>
            <ul v-else class="space-y-2">
              <li v-for="r in runs" :key="r.id"
                  class="border border-neutral-200 rounded-lg p-3">
                <div class="flex items-start gap-2">
                  <span class="px-1.5 py-0.5 text-[10px] font-semibold rounded uppercase flex-shrink-0 mt-0.5"
                        :class="runStatusBadge(r.status)">{{ r.status || '?' }}</span>
                  <div class="min-w-0 flex-1">
                    <div class="text-xs text-fg-secondary font-mono">{{ formatTime(r.fired_at) }}</div>
                    <div v-if="r.finished_at" class="text-[11px] text-fg-tertiary mt-0.5">
                      完成於 {{ relTime(r.finished_at) }}（耗時 {{ duration(r.fired_at, r.finished_at) }}）
                    </div>
                    <div v-if="r.tokens_used || r.cost_usd" class="text-[11px] text-fg-tertiary mt-0.5 flex gap-2">
                      <span v-if="r.tokens_used">🔤 {{ r.tokens_used.toLocaleString() }} tokens</span>
                      <span v-if="r.cost_usd">💰 ${{ r.cost_usd.toFixed(4) }}</span>
                    </div>
                    <p v-if="r.output_summary" class="text-xs text-fg mt-2 whitespace-pre-wrap line-clamp-4">
                      {{ r.output_summary }}
                    </p>
                    <p v-if="r.error" class="text-xs text-danger-700 mt-2 px-2 py-1.5 bg-danger-50 rounded">
                      {{ r.error }}
                    </p>
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
import { computed, onMounted, reactive, ref } from 'vue'
import { SIcon, SSpinner } from '@staffkm/ui-kit'
import { triggerApi, type Trigger, type TriggerRun, type TriggerKind } from '../../api/trigger'
import { applicationApi, type Application } from '../../api/application'
import EmptyState from '../../components/common/EmptyState.vue'

const loading = ref(true)
const triggers = ref<Trigger[]>([])
const apps = ref<Application[]>([])

const showDialog = ref(false)
const editingId = ref<string | null>(null)
const submitting = ref(false)
const draft = reactive({
  application_id: '',
  name: '',
  kind: 'interval' as TriggerKind,
  cron_expr: '',
  interval_sec: 3600,
  input_template: '',
  enabled: true,
})

const runsOpen = ref(false)
const runsTarget = ref<Trigger | null>(null)
const runsLoading = ref(false)
const runs = ref<TriggerRun[]>([])

async function loadAll() {
  loading.value = true
  try {
    const [trRes, appRes] = await Promise.allSettled([
      triggerApi.list(),
      applicationApi.list({ page_size: 100 }),
    ])
    if (trRes.status === 'fulfilled') triggers.value = trRes.value
    if (appRes.status === 'fulfilled') {
      const v = appRes.value
      apps.value = v.data.data?.items ?? v.data.data ?? []
    }
  } finally {
    loading.value = false
  }
}

function appName(id: string): string {
  return apps.value.find(a => a.id === id)?.name || id.slice(0, 8)
}

function reset() {
  draft.application_id = apps.value[0]?.id || ''
  draft.name = ''
  draft.kind = 'interval'
  draft.cron_expr = ''
  draft.interval_sec = 3600
  draft.input_template = ''
  draft.enabled = true
  editingId.value = null
}

function openCreate() { reset(); showDialog.value = true }

function openEdit(t: Trigger) {
  editingId.value = t.id
  draft.application_id = t.application_id
  draft.name = t.name
  draft.kind = t.kind
  draft.cron_expr = t.cron_expr || ''
  draft.interval_sec = t.interval_sec || 3600
  draft.input_template = ''  // backend 沒回傳，編輯不改
  draft.enabled = t.enabled
  showDialog.value = true
}

const canSubmit = computed(() => {
  if (!draft.name.trim() || !draft.application_id) return false
  if (draft.kind === 'interval' && (!draft.interval_sec || draft.interval_sec < 10)) return false
  if (draft.kind === 'cron' && !draft.cron_expr.trim()) return false
  return true
})

async function onSubmit() {
  submitting.value = true
  try {
    if (editingId.value) {
      await triggerApi.update(editingId.value, {
        name: draft.name,
        cron_expr: draft.kind === 'cron' ? draft.cron_expr : null,
        interval_sec: draft.kind === 'interval' ? draft.interval_sec : null,
        input_template: draft.input_template,
        enabled: draft.enabled,
      })
    } else {
      await triggerApi.create({
        application_id: draft.application_id,
        name: draft.name,
        kind: draft.kind,
        cron_expr: draft.kind === 'cron' ? draft.cron_expr : undefined,
        interval_sec: draft.kind === 'interval' ? draft.interval_sec : undefined,
        input_template: draft.input_template,
        enabled: draft.enabled,
      })
    }
    showDialog.value = false
    await loadAll()
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '失敗')
  } finally {
    submitting.value = false
  }
}

async function toggleEnabled(t: Trigger) {
  await triggerApi.update(t.id, { enabled: !t.enabled })
  await loadAll()
}

async function confirmDelete(t: Trigger) {
  if (!confirm(`刪除 trigger「${t.name}」？歷史 runs 會一併移除。`)) return
  await triggerApi.remove(t.id)
  await loadAll()
}

async function openRuns(t: Trigger) {
  runsTarget.value = t
  runsOpen.value = true
  runsLoading.value = true
  try {
    runs.value = await triggerApi.listRuns(t.id)
  } finally {
    runsLoading.value = false
  }
}

// — formatters —
function kindBadge(k: TriggerKind): string {
  switch (k) {
    case 'interval': return 'bg-info-50 text-info-700'
    case 'cron':     return 'bg-brand-50 text-brand-700'
    case 'webhook':  return 'bg-warning-50 text-warning-700'
  }
}
function statusBadge(t: Trigger): string {
  if (!t.enabled) return 'bg-neutral-100 text-fg-tertiary'
  switch (t.last_status) {
    case 'ok':       return 'bg-success-50 text-success-700'
    case 'failed':   return 'bg-danger-50 text-danger-700'
    case 'running':  return 'bg-warning-50 text-warning-700'
    case 'pending':  return 'bg-info-50 text-info-700'
    default:         return 'bg-neutral-100 text-fg-tertiary'
  }
}
function statusLabel(t: Trigger): string {
  if (!t.enabled) return '已停用'
  if (!t.last_status) return '等待首次觸發'
  return ({ ok:'成功', failed:'失敗', running:'執行中', pending:'排程中', cancelled:'已取消' } as any)[t.last_status] || t.last_status
}
function runStatusBadge(s: RunStatus): string {
  switch (s) {
    case 'ok':       return 'bg-success-50 text-success-700'
    case 'failed':   return 'bg-danger-50 text-danger-700'
    case 'running':  return 'bg-warning-50 text-warning-700'
    case 'pending':  return 'bg-info-50 text-info-700'
    case 'cancelled':return 'bg-neutral-100 text-fg-tertiary'
    default:         return 'bg-neutral-100 text-fg-tertiary'
  }
}
type RunStatus = TriggerRun['status']

function relTime(iso: string, future = false): string {
  const t = new Date(iso).getTime()
  if (isNaN(t)) return iso
  const diff = future ? Math.floor((t - Date.now()) / 1000) : Math.floor((Date.now() - t) / 1000)
  if (diff < 0)     return future ? '已過' : '剛剛'
  if (diff < 60)    return future ? `${diff}s 後` : `${diff} 秒前`
  if (diff < 3600)  return future ? `${Math.floor(diff/60)}m 後` : `${Math.floor(diff/60)} 分鐘前`
  if (diff < 86400) return future ? `${Math.floor(diff/3600)}h 後` : `${Math.floor(diff/3600)} 小時前`
  return future ? `${Math.floor(diff/86400)}d 後` : `${Math.floor(diff/86400)} 天前`
}
function formatTime(iso: string): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  return d.toLocaleString('zh-TW', { hour12: false })
}
function duration(start: string, end: string): string {
  const ms = new Date(end).getTime() - new Date(start).getTime()
  if (ms < 1000)   return `${ms}ms`
  if (ms < 60000)  return `${(ms/1000).toFixed(1)}s`
  return `${Math.floor(ms/60000)}m${Math.floor((ms%60000)/1000)}s`
}

onMounted(loadAll)
</script>
