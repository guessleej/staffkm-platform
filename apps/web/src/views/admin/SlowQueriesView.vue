<template>
  <div class="flex flex-col h-full">
    <!-- 頁首 -->
    <div class="px-6 py-5 flex-shrink-0">
      <div class="card-hero flex items-center justify-between gap-4">
        <div>
          <h1 class="heading-page heading-accent">Slow Query Analyzer</h1>
          <p class="text-sm text-fg-tertiary mt-1">自動捕獲 &gt; 500ms 的 SQL 與 EXPLAIN ANALYZE plan（v3.8 P4）</p>
        </div>
        <button
          @click="load"
          class="btn btn-warm"
        >
          <SIcon name="refresh" :size="12" /> 重新整理
        </button>
      </div>
    </div>

    <!-- Tab 切換 -->
    <div class="bg-surface-raised border-b border-bd px-6 flex items-center gap-1 flex-shrink-0">
      <button
        v-for="t in tabs"
        :key="t.key"
        @click="tab = t.key"
        class="px-3 py-2 text-sm border-b-2 transition"
        :class="tab === t.key
          ? 'border-brand-500 text-fg font-medium'
          : 'border-transparent text-fg-secondary hover:text-fg'"
      >
        {{ t.label }}
      </button>
    </div>

    <!-- 內容 -->
    <div class="flex-1 overflow-y-auto p-6">
      <div v-if="loading" class="flex justify-center py-20">
        <SSpinner :size="24" />
      </div>

      <!-- 最近 slow tab -->
      <template v-else-if="tab === 'recent'">
        <div v-if="!recent.length" class="text-center py-20">
          <div class="w-12 h-12 bg-brand-50 rounded-2xl flex items-center justify-center mx-auto mb-3">
            <SIcon name="database" :size="24" :stroke-width="1.5" class="text-brand-500" />
          </div>
          <p class="text-fg-secondary font-medium">過去 24 小時無慢查詢</p>
          <p class="text-xs text-fg-tertiary mt-1">系統健康 — 沒有 query 超過門檻</p>
        </div>

        <table v-else class="w-full text-sm bg-surface-raised border border-bd rounded-2xl overflow-hidden shadow-sm">
          <thead>
            <tr class="bg-surface-sunken text-xs uppercase tracking-wider text-fg-tertiary text-left">
              <th class="px-4 py-3 font-semibold">時間</th>
              <th class="px-4 py-3 font-semibold text-right">耗時 (ms)</th>
              <th class="px-4 py-3 font-semibold">SQL（截斷）</th>
              <th class="px-4 py-3 font-semibold text-center">Plan</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in recent"
              :key="row.id"
              class="border-t border-neutral-100 hover:bg-neutral-50/40 transition cursor-pointer"
              @click="openDetail(row.id)"
            >
              <td class="px-4 py-3 text-fg-secondary text-xs whitespace-nowrap">{{ fmt(row.captured_at) }}</td>
              <td class="px-4 py-3 text-right font-mono text-xs" :class="durationClass(row.duration_ms)">
                {{ row.duration_ms.toLocaleString() }}
              </td>
              <td class="px-4 py-3 font-mono text-xs text-fg truncate max-w-[600px]" :title="row.sql_text">
                {{ truncate(row.sql_text, 120) }}
              </td>
              <td class="px-4 py-3 text-center">
                <span v-if="row.explain_error" class="inline-flex items-center px-2 py-0.5 rounded-md text-xs bg-danger-50 text-danger-700">
                  錯誤
                </span>
                <span v-else-if="row.has_plan" class="inline-flex items-center px-2 py-0.5 rounded-md text-xs bg-success-50 text-success-700">
                  有 plan
                </span>
                <span v-else class="text-fg-tertiary text-xs">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </template>

      <!-- 依 hash 聚合 tab -->
      <template v-else>
        <div v-if="!aggregates.length" class="text-center py-20">
          <div class="w-12 h-12 bg-brand-50 rounded-2xl flex items-center justify-center mx-auto mb-3">
            <SIcon name="database" :size="24" :stroke-width="1.5" class="text-brand-500" />
          </div>
          <p class="text-fg-secondary font-medium">過去 24 小時無資料</p>
        </div>

        <table v-else class="w-full text-sm bg-surface-raised border border-bd rounded-2xl overflow-hidden shadow-sm">
          <thead>
            <tr class="bg-surface-sunken text-xs uppercase tracking-wider text-fg-tertiary text-left">
              <th class="px-4 py-3 font-semibold">SQL Hash</th>
              <th class="px-4 py-3 font-semibold text-right">出現次數</th>
              <th class="px-4 py-3 font-semibold text-right">Max (ms)</th>
              <th class="px-4 py-3 font-semibold text-right">Avg (ms)</th>
              <th class="px-4 py-3 font-semibold">代表 SQL</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in aggregates"
              :key="row.sql_hash"
              class="border-t border-neutral-100 hover:bg-neutral-50/40 transition"
            >
              <td class="px-4 py-3 font-mono text-xs text-fg-secondary">{{ row.sql_hash.slice(0, 12) }}</td>
              <td class="px-4 py-3 text-right text-fg font-medium">{{ row.occurrences }}</td>
              <td class="px-4 py-3 text-right font-mono text-xs" :class="durationClass(row.max_ms)">
                {{ row.max_ms.toLocaleString() }}
              </td>
              <td class="px-4 py-3 text-right font-mono text-xs text-fg-secondary">
                {{ row.avg_ms.toLocaleString() }}
              </td>
              <td class="px-4 py-3 font-mono text-xs text-fg-secondary truncate max-w-[500px]" :title="row.sample_sql">
                {{ truncate(row.sample_sql, 100) }}
              </td>
            </tr>
          </tbody>
        </table>
      </template>
    </div>

    <!-- 詳情抽屜 -->
    <div
      v-if="detailOpen"
      class="fixed inset-0 bg-black/40 z-40 flex justify-end"
      @click.self="detailOpen = false"
    >
      <div class="w-full max-w-3xl h-full bg-surface-raised shadow-xl overflow-y-auto">
        <div class="px-6 py-4 border-b border-neutral-200 flex items-center justify-between sticky top-0 bg-surface-raised z-10">
          <div>
            <h2 class="text-base font-semibold text-fg">Slow Query Detail</h2>
            <p v-if="detail" class="text-xs text-fg-tertiary mt-0.5">
              {{ fmt(detail.captured_at) }} · {{ detail.duration_ms.toLocaleString() }} ms
            </p>
          </div>
          <button
            @click="detailOpen = false"
            class="p-1.5 text-fg-secondary hover:text-fg rounded hover:bg-neutral-100"
          >
            <SIcon name="x" :size="18" />
          </button>
        </div>

        <div v-if="detailLoading" class="flex justify-center py-20">
          <SSpinner :size="24" />
        </div>

        <div v-else-if="detail" class="p-6 space-y-5">
          <section>
            <h3 class="text-xs uppercase tracking-wider text-fg-tertiary mb-2">SQL</h3>
            <pre class="text-xs font-mono bg-surface-sunken p-3 rounded-lg border border-neutral-200 whitespace-pre-wrap break-all max-h-64 overflow-y-auto">{{ detail.sql_text }}</pre>
          </section>

          <section v-if="detail.explain_error">
            <h3 class="text-xs uppercase tracking-wider text-fg-tertiary mb-2">EXPLAIN 錯誤</h3>
            <pre class="text-xs font-mono bg-danger-50 text-danger-700 p-3 rounded-lg whitespace-pre-wrap break-all">{{ detail.explain_error }}</pre>
          </section>

          <section v-if="detail.explain_json">
            <h3 class="text-xs uppercase tracking-wider text-fg-tertiary mb-2">Execution Plan</h3>
            <pre class="text-xs font-mono bg-surface-sunken p-3 rounded-lg border border-neutral-200 whitespace-pre-wrap break-all max-h-[60vh] overflow-y-auto">{{ JSON.stringify(detail.explain_json, null, 2) }}</pre>
          </section>

          <section v-else-if="!detail.explain_error">
            <p class="text-xs text-fg-tertiary">無 plan（可能查詢含 bind params 而被跳過）。</p>
          </section>

          <section>
            <h3 class="text-xs uppercase tracking-wider text-fg-tertiary mb-2">Metadata</h3>
            <dl class="text-xs grid grid-cols-[120px_1fr] gap-y-1 text-fg-secondary">
              <dt class="text-fg-tertiary">SQL Hash</dt>
              <dd class="font-mono">{{ detail.sql_hash }}</dd>
              <dt class="text-fg-tertiary">Capture ID</dt>
              <dd class="font-mono">{{ detail.id }}</dd>
            </dl>
          </section>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { SIcon, SSpinner } from '@staffkm/ui-kit'
import { slowQueriesApi, type SlowQueryRow, type SlowQueryAggregate, type SlowQueryDetail } from '../../api/slowQueries'

type TabKey = 'recent' | 'aggregate'

const tabs: { key: TabKey; label: string }[] = [
  { key: 'recent',    label: '最近 slow（24h）' },
  { key: 'aggregate', label: '依 hash 聚合' },
]

const tab = ref<TabKey>('recent')
const loading = ref(true)
const recent = ref<SlowQueryRow[]>([])
const aggregates = ref<SlowQueryAggregate[]>([])

const detailOpen = ref(false)
const detailLoading = ref(false)
const detail = ref<SlowQueryDetail | null>(null)

async function load() {
  loading.value = true
  try {
    const [r, a] = await Promise.all([
      slowQueriesApi.list(),
      slowQueriesApi.topByHash(),
    ])
    recent.value = r.items || []
    aggregates.value = a.items || []
  } catch (e) {
    console.warn('slow_queries_load_failed', e)
  } finally {
    loading.value = false
  }
}

async function openDetail(id: string) {
  detailOpen.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await slowQueriesApi.detail(id)
  } catch (e) {
    console.warn('slow_query_detail_failed', e)
  } finally {
    detailLoading.value = false
  }
}

function durationClass(ms: number): string {
  if (ms >= 2000) return 'text-danger-700 font-semibold'
  if (ms >= 1000) return 'text-warning-700 font-medium'
  return 'text-fg'
}

function truncate(s: string, n: number): string {
  if (!s) return ''
  return s.length > n ? s.slice(0, n) + '…' : s
}

function fmt(ts: string | null): string {
  if (!ts) return '—'
  try { return new Date(ts).toLocaleString('zh-TW', { hour12: false }) }
  catch { return ts }
}

onMounted(load)
</script>
