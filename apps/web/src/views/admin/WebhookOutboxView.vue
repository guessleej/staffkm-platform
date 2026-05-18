<template>
  <div class="flex flex-col h-full">
    <!-- 頁首 -->
    <div class="bg-surface-raised border-b border-neutral-200 px-6 py-4 flex items-center justify-between flex-shrink-0">
      <div>
        <h1 class="text-lg font-semibold text-fg">Webhook Outbox</h1>
        <p class="text-sm text-fg-tertiary mt-0.5">系統外送 webhook 派發狀態與失敗重試（v3.6 P1）</p>
      </div>
      <div class="flex items-center gap-2">
        <button
          @click="load"
          class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50 transition flex items-center gap-1"
        >
          <SIcon name="refresh" :size="12" /> 重新整理
        </button>
      </div>
    </div>

    <!-- status filter chips -->
    <div class="px-6 pt-4 flex items-center gap-2 flex-shrink-0">
      <button
        v-for="opt in FILTER_OPTS"
        :key="opt.value || 'all'"
        @click="setFilter(opt.value)"
        class="px-3 py-1.5 text-xs rounded-full border transition"
        :class="filter === opt.value
          ? 'bg-brand-600 text-white border-brand-600'
          : 'bg-surface-raised text-fg-secondary border-neutral-200 hover:bg-neutral-50'"
      >{{ opt.label }}</button>
    </div>

    <!-- table -->
    <div class="flex-1 overflow-y-auto p-6">
      <div v-if="loading" class="flex justify-center py-20">
        <SSpinner :size="24" />
      </div>

      <div v-else-if="!items.length" class="text-center py-20">
        <div class="w-12 h-12 bg-brand-50 rounded-2xl flex items-center justify-center mx-auto mb-3">
          <SIcon name="send" :size="24" :stroke-width="1.5" class="text-brand-500" />
        </div>
        <p class="text-fg-secondary font-medium">沒有符合條件的 outbox 紀錄</p>
      </div>

      <table v-else class="w-full text-sm bg-surface-raised border border-neutral-200 rounded-xl overflow-hidden">
        <thead>
          <tr class="bg-surface-sunken text-xs uppercase tracking-wider text-fg-tertiary text-left">
            <th class="px-4 py-3 font-semibold">建立時間</th>
            <th class="px-4 py-3 font-semibold">URL</th>
            <th class="px-4 py-3 font-semibold">Method</th>
            <th class="px-4 py-3 font-semibold text-center">狀態</th>
            <th class="px-4 py-3 font-semibold text-center">次數</th>
            <th class="px-4 py-3 font-semibold">最後錯誤</th>
            <th class="px-4 py-3 font-semibold text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="row in items" :key="row.id">
            <tr class="border-t border-neutral-100 hover:bg-neutral-50/40 transition align-top cursor-pointer"
                @click="toggleExpand(row.id)">
              <td class="px-4 py-3 text-fg-secondary whitespace-nowrap">{{ fmt(row.created_at) }}</td>
              <td class="px-4 py-3 max-w-[280px] truncate font-mono text-xs text-fg-secondary" :title="row.url">
                {{ row.url }}
              </td>
              <td class="px-4 py-3 text-fg-secondary text-xs">{{ row.method }}</td>
              <td class="px-4 py-3 text-center">
                <span class="inline-flex items-center px-2 py-0.5 rounded-md text-xs"
                      :class="statusClass(row.status)">
                  {{ statusLabel(row.status) }}
                </span>
              </td>
              <td class="px-4 py-3 text-center text-fg-secondary">{{ row.attempts }}</td>
              <td class="px-4 py-3 max-w-[280px]">
                <div v-if="row.last_error"
                     class="text-danger-700 text-xs whitespace-pre-wrap break-words line-clamp-2">
                  {{ row.last_error }}
                </div>
                <span v-else class="text-fg-tertiary text-xs">—</span>
                <div v-if="row.last_status_code !== null" class="text-[10px] text-fg-tertiary mt-0.5">
                  HTTP {{ row.last_status_code }}
                </div>
              </td>
              <td class="px-4 py-3 text-right whitespace-nowrap">
                <button
                  v-if="row.status === 'failed' || row.status === 'pending'"
                  @click.stop="retry(row)"
                  :disabled="retrying === row.id"
                  class="px-2.5 py-1 text-xs text-brand-700 hover:bg-brand-50 rounded-md transition disabled:opacity-50"
                  title="立即重試"
                >
                  <SIcon name="refresh" :size="14" />
                </button>
                <span v-else-if="row.status === 'delivered'" class="text-xs text-fg-tertiary">
                  {{ fmt(row.delivered_at) }}
                </span>
              </td>
            </tr>
            <tr v-if="expanded === row.id && row.last_error" class="border-t border-neutral-100 bg-neutral-50/40">
              <td colspan="7" class="px-4 py-3">
                <div class="text-[11px] text-fg-tertiary mb-1">完整錯誤訊息：</div>
                <pre class="text-xs text-danger-700 whitespace-pre-wrap break-words">{{ row.last_error }}</pre>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { SIcon, SSpinner } from '@staffkm/ui-kit'
import { webhookOutboxApi, type WebhookOutboxRow } from '../../api/webhookOutbox'

type OutboxStatus = WebhookOutboxRow['status']

const FILTER_OPTS: { value: OutboxStatus | undefined; label: string }[] = [
  { value: undefined,    label: '全部' },
  { value: 'pending',    label: '待派發' },
  { value: 'in_flight',  label: '派發中' },
  { value: 'failed',     label: 'DLQ（失敗）' },
  { value: 'delivered',  label: '已送達' },
]

const items    = ref<WebhookOutboxRow[]>([])
const loading  = ref(true)
const filter   = ref<OutboxStatus | undefined>(undefined)
const expanded = ref<string | null>(null)
const retrying = ref<string | null>(null)

async function load() {
  loading.value = true
  try {
    const res = await webhookOutboxApi.list(filter.value)
    items.value = res.items || []
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '載入失敗')
  } finally {
    loading.value = false
  }
}

function setFilter(v: OutboxStatus | undefined) {
  filter.value = v
  load()
}

function toggleExpand(id: string) {
  expanded.value = expanded.value === id ? null : id
}

async function retry(row: WebhookOutboxRow) {
  retrying.value = row.id
  try {
    await webhookOutboxApi.retry(row.id)
    await load()
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '重試失敗')
  } finally {
    retrying.value = null
  }
}

function statusClass(s: OutboxStatus): string {
  if (s === 'pending')   return 'bg-warning-50 text-warning-700'
  if (s === 'in_flight') return 'bg-brand-50 text-brand-700'
  if (s === 'delivered') return 'bg-success-50 text-success-700'
  return 'bg-danger-50 text-danger-700'
}

function statusLabel(s: OutboxStatus): string {
  return s === 'pending'   ? '待派發'
       : s === 'in_flight' ? '派發中'
       : s === 'delivered' ? '已送達'
       : 'DLQ'
}

function fmt(ts: string | null): string {
  if (!ts) return '—'
  try { return new Date(ts).toLocaleString('zh-TW', { hour12: false }) }
  catch { return ts }
}

onMounted(load)
</script>
