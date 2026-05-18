<template>
  <div class="flex flex-col h-full">
    <!-- 頁首 -->
    <div class="bg-surface-raised border-b border-neutral-200 px-6 py-4 flex items-center justify-between flex-shrink-0">
      <div>
        <h1 class="text-lg font-semibold text-fg">Worker Heartbeats</h1>
        <p class="text-sm text-fg-tertiary mt-0.5">背景 worker loop 健康狀態（v3.6 P2）</p>
      </div>
      <div class="flex items-center gap-2">
        <span class="text-xs text-fg-tertiary">每 30 秒自動刷新</span>
        <button
          @click="load"
          class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50 transition flex items-center gap-1"
        >
          <SIcon name="refresh" :size="12" /> 重新整理
        </button>
      </div>
    </div>

    <!-- 表格 -->
    <div class="flex-1 overflow-y-auto p-6">
      <div v-if="loading && !items.length" class="flex justify-center py-20">
        <SSpinner :size="24" />
      </div>

      <div v-else-if="!items.length" class="text-center py-20">
        <div class="w-12 h-12 bg-brand-50 rounded-2xl flex items-center justify-center mx-auto mb-3">
          <SIcon name="loader" :size="24" :stroke-width="1.5" class="text-brand-500" />
        </div>
        <p class="text-fg-secondary font-medium">尚無 worker 心跳紀錄</p>
        <p class="text-xs text-fg-tertiary mt-1">背景 worker 首次運行後會出現於此</p>
      </div>

      <table v-else class="w-full text-sm bg-surface-raised border border-neutral-200 rounded-xl overflow-hidden">
        <thead>
          <tr class="bg-surface-sunken text-xs uppercase tracking-wider text-fg-tertiary text-left">
            <th class="px-4 py-3 font-semibold">Worker</th>
            <th class="px-4 py-3 font-semibold">Host (pid)</th>
            <th class="px-4 py-3 font-semibold">啟動時間</th>
            <th class="px-4 py-3 font-semibold">最後心跳</th>
            <th class="px-4 py-3 font-semibold text-center">In Flight</th>
            <th class="px-4 py-3 font-semibold text-center">狀態</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in items"
            :key="row.worker_name"
            class="border-t border-neutral-100 hover:bg-neutral-50/40 transition"
          >
            <td class="px-4 py-3 font-mono text-xs text-fg">{{ row.worker_name }}</td>
            <td class="px-4 py-3 text-fg-secondary text-xs">
              {{ row.host || '—' }}<span v-if="row.pid" class="text-fg-tertiary"> ({{ row.pid }})</span>
            </td>
            <td class="px-4 py-3 text-fg-secondary text-xs whitespace-nowrap">{{ fmt(row.started_at) }}</td>
            <td class="px-4 py-3 text-fg-secondary text-xs whitespace-nowrap">
              {{ relative(row.stale_seconds) }}
              <div class="text-[10px] text-fg-tertiary">{{ fmt(row.last_beat) }}</div>
            </td>
            <td class="px-4 py-3 text-center text-fg-secondary">{{ row.in_flight }}</td>
            <td class="px-4 py-3 text-center">
              <span
                class="inline-flex items-center px-2 py-0.5 rounded-md text-xs"
                :class="pillClass(row.stale_seconds)"
              >
                {{ pillLabel(row.stale_seconds) }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>

      <p v-if="items.length" class="mt-3 text-xs text-fg-tertiary">
        stale 門檻：{{ staleThreshold }} 秒（&gt; 5 分鐘無心跳 → 紅燈）
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { SIcon, SSpinner } from '@staffkm/ui-kit'
import { heartbeatsApi, type WorkerHeartbeat } from '../../api/heartbeats'

const items = ref<WorkerHeartbeat[]>([])
const loading = ref(true)
const staleThreshold = ref(300)
let timer: number | null = null

async function load() {
  loading.value = true
  try {
    const res = await heartbeatsApi.list()
    items.value = res.items || []
    staleThreshold.value = res.stale_threshold_sec || 300
  } catch (e: any) {
    // 靜默：自動刷新時不彈窗
    if (!items.value.length) {
      console.warn('heartbeats_load_failed', e)
    }
  } finally {
    loading.value = false
  }
}

function pillClass(stale: number): string {
  if (stale < 120) return 'bg-success-50 text-success-700'
  if (stale < 300) return 'bg-warning-50 text-warning-700'
  return 'bg-danger-50 text-danger-700'
}

function pillLabel(stale: number): string {
  if (stale < 120) return '健康'
  if (stale < 300) return '延遲'
  return '失聯'
}

function relative(seconds: number): string {
  if (seconds < 60) return `${seconds} 秒前`
  if (seconds < 3600) return `${Math.floor(seconds / 60)} 分鐘前`
  return `${Math.floor(seconds / 3600)} 小時前`
}

function fmt(ts: string | null): string {
  if (!ts) return '—'
  try { return new Date(ts).toLocaleString('zh-TW', { hour12: false }) }
  catch { return ts }
}

onMounted(() => {
  load()
  timer = window.setInterval(load, 30_000)
})

onBeforeUnmount(() => {
  if (timer !== null) window.clearInterval(timer)
})
</script>
