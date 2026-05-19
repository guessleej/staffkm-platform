<template>
  <div class="p-6 h-full flex flex-col">
    <div class="card-hero mb-4">
      <h1 class="heading-page heading-accent">Workflow 執行紀錄</h1>
    </div>

    <!-- application select -->
    <div class="mb-4">
      <label class="text-sm text-fg-secondary mr-2">應用：</label>
      <select v-model="selectedAppId" @change="loadRuns" class="px-3 py-1.5 border border-bd rounded text-sm bg-surface-raised">
        <option value="">(請選擇)</option>
        <option v-for="a in apps" :key="a.id" :value="a.id">{{ a.name }}</option>
      </select>
    </div>

    <div class="flex-1 grid grid-cols-12 gap-4 overflow-hidden">
      <!-- 左：runs -->
      <aside class="col-span-4 overflow-y-auto border border-bd rounded p-2 space-y-2">
        <p v-if="!selectedAppId" class="text-sm text-fg-tertiary p-3">先選一個 application</p>
        <p v-else-if="loadingRuns" class="text-sm text-fg-tertiary p-3">載入中…</p>
        <p v-else-if="runs.length === 0" class="text-sm text-fg-tertiary p-3">尚無 run</p>
        <button
          v-for="r in runs" :key="r.id"
          @click="selectRun(r)"
          :class="['w-full text-left p-3 rounded border transition', selectedRunId === r.id ? 'border-brand-500 bg-brand-50' : 'border-bd hover:bg-neutral-50']"
        >
          <div class="flex items-center justify-between mb-1">
            <span class="text-xs text-fg-secondary font-mono">{{ formatTime(r.fired_at) }}</span>
            <span :class="['text-[10px] px-1.5 py-0.5 rounded uppercase font-semibold', statusBadge(r.status)]">{{ r.status }}</span>
          </div>
          <div class="text-sm text-fg truncate">{{ r.trigger_name }}</div>
          <div class="text-[11px] text-fg-tertiary mt-1 flex gap-2" v-if="r.tokens_used || r.cost_usd">
            <span v-if="r.tokens_used">🔤 {{ r.tokens_used.toLocaleString() }}</span>
            <span v-if="r.cost_usd">💰 ${{ r.cost_usd.toFixed(4) }}</span>
          </div>
        </button>
      </aside>

      <!-- 右：steps -->
      <main class="col-span-8 overflow-y-auto border border-bd rounded p-4">
        <p v-if="!selectedRunId" class="text-sm text-fg-tertiary">選一個 run 看 step 詳細</p>
        <p v-else-if="loadingSteps" class="text-sm text-fg-tertiary">載入中…</p>
        <ol v-else class="space-y-2">
          <li
            v-for="s in steps" :key="s.id"
            :class="['border rounded p-3', stepBorderClass(s.status)]"
          >
            <button @click="toggleStep(s.id)" class="w-full text-left">
              <div class="flex items-center gap-2">
                <span class="text-xs font-mono text-fg-secondary w-8">#{{ s.step_index }}</span>
                <span class="font-medium text-sm">{{ s.node_key }}</span>
                <span class="text-xs text-fg-tertiary">({{ s.node_type }})</span>
                <span :class="['ml-auto text-[10px] px-1.5 py-0.5 rounded uppercase font-semibold', stepStatusBadge(s.status)]">{{ s.status }}</span>
                <span v-if="s.latency_ms !== null" class="text-[11px] text-fg-tertiary">{{ s.latency_ms }}ms</span>
                <span v-if="s.attempts > 1" class="text-[11px] text-warning-700">×{{ s.attempts }}</span>
              </div>
              <p v-if="s.error" class="text-xs text-danger-700 mt-1 truncate">{{ s.error }}</p>
            </button>
            <div v-if="expandedSteps.has(s.id)" class="mt-3 grid grid-cols-2 gap-2">
              <div>
                <div class="text-xs font-semibold text-fg-secondary mb-1">Input</div>
                <pre class="text-[11px] bg-neutral-50 p-2 rounded overflow-auto max-h-60">{{ JSON.stringify(s.input_snapshot, null, 2) }}</pre>
              </div>
              <div>
                <div class="text-xs font-semibold text-fg-secondary mb-1">Output</div>
                <pre class="text-[11px] bg-neutral-50 p-2 rounded overflow-auto max-h-60">{{ JSON.stringify(s.output_snapshot, null, 2) }}</pre>
              </div>
            </div>
          </li>
        </ol>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { runHistoryApi, type WorkflowRun, type WorkflowRunStep } from '@/api/runHistory'
import { applicationApi } from '@/api/application'

const apps = ref<any[]>([])
const selectedAppId = ref('')
const runs = ref<WorkflowRun[]>([])
const selectedRunId = ref('')
const steps = ref<WorkflowRunStep[]>([])
const loadingRuns = ref(false)
const loadingSteps = ref(false)
const expandedSteps = ref(new Set<string>())

onMounted(async () => {
  try {
    const v = await applicationApi.list({ page_size: 100 })
    apps.value = v.data.data?.items ?? v.data.data ?? []
  } catch (e) {
    console.error('load apps failed', e)
  }
})

async function loadRuns() {
  if (!selectedAppId.value) return
  loadingRuns.value = true
  selectedRunId.value = ''
  steps.value = []
  try {
    runs.value = (await runHistoryApi.listRuns(selectedAppId.value)).items
  } finally { loadingRuns.value = false }
}

async function selectRun(r: WorkflowRun) {
  selectedRunId.value = r.id
  expandedSteps.value = new Set()
  loadingSteps.value = true
  try {
    steps.value = (await runHistoryApi.listSteps(selectedAppId.value, r.id)).items
  } finally { loadingSteps.value = false }
}

function toggleStep(id: string) {
  if (expandedSteps.value.has(id)) expandedSteps.value.delete(id)
  else expandedSteps.value.add(id)
  // 強制 reactivity
  expandedSteps.value = new Set(expandedSteps.value)
}

function formatTime(t: string): string {
  return new Date(t).toLocaleString('zh-TW', { hour12: false })
}

function statusBadge(s: string): string {
  return ({
    ok: 'bg-success-100 text-success-700',
    error: 'bg-danger-100 text-danger-700',
    paused: 'bg-violet-100 text-violet-700',
    rejected: 'bg-neutral-200 text-neutral-700',
    queued: 'bg-brand-100 text-brand-700',
    running: 'bg-warning-100 text-warning-700',
    quota_exceeded: 'bg-danger-100 text-danger-700',
  } as Record<string, string>)[s] || 'bg-neutral-100 text-neutral-700'
}

function stepStatusBadge(s: string): string {
  return ({
    ok: 'bg-success-100 text-success-700',
    error: 'bg-danger-100 text-danger-700',
    retry: 'bg-warning-100 text-warning-700',
    paused: 'bg-violet-100 text-violet-700',
  } as Record<string, string>)[s] || 'bg-neutral-100 text-neutral-700'
}

function stepBorderClass(s: string): string {
  if (s === 'error') return 'border-danger-200'
  if (s === 'retry') return 'border-warning-200'
  if (s === 'paused') return 'border-violet-200'
  return 'border-bd'
}
</script>
