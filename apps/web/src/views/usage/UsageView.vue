<template>
  <div class="flex flex-col h-full">
    <!-- 頁首 -->
    <div class="bg-surface-raised border-b border-neutral-200 px-6 py-4 flex items-center justify-between flex-shrink-0">
      <div>
        <h1 class="text-lg font-semibold text-fg">當月用量</h1>
        <p class="text-sm text-fg-tertiary mt-0.5">當前 workspace · {{ summary?.month || '—' }}</p>
      </div>
      <button
        @click="load"
        class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50 transition flex items-center gap-1"
      >
        <SIcon name="refresh" :size="12" /> 重新整理
      </button>
    </div>

    <div class="flex-1 overflow-y-auto p-6 space-y-6">
      <div v-if="loading" class="flex justify-center py-20">
        <SSpinner :size="24" />
      </div>

      <template v-else-if="summary">
        <!-- 4 個 stat card -->
        <section class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="bg-surface-raised rounded-xl border border-neutral-200 p-4">
            <p class="text-xs text-fg-tertiary">本月 tokens</p>
            <p class="text-2xl font-semibold text-fg mt-1 tabular-nums">
              {{ fmtNum(summary.usage.tokens) }}
            </p>
          </div>
          <div class="bg-surface-raised rounded-xl border border-neutral-200 p-4">
            <p class="text-xs text-fg-tertiary">本月成本 (USD)</p>
            <p class="text-2xl font-semibold text-fg mt-1 tabular-nums">
              ${{ Number(summary.usage.cost_usd).toFixed(4) }}
            </p>
          </div>
          <div class="bg-surface-raised rounded-xl border border-neutral-200 p-4">
            <p class="text-xs text-fg-tertiary">請求數</p>
            <p class="text-2xl font-semibold text-fg mt-1 tabular-nums">
              {{ fmtNum(summary.usage.requests) }}
            </p>
          </div>
          <div class="bg-surface-raised rounded-xl border border-neutral-200 p-4">
            <p class="text-xs text-fg-tertiary">Quota 剩餘</p>
            <p class="text-2xl font-semibold mt-1 tabular-nums"
               :class="quotaRemainColor">
              {{ quotaRemainLabel }}
            </p>
            <p class="text-[10px] text-fg-tertiary mt-0.5">{{ quotaRemainHint }}</p>
          </div>
        </section>

        <!-- by_day bar chart -->
        <section class="bg-surface-raised rounded-xl border border-neutral-200 p-5">
          <h2 class="text-sm font-semibold text-fg mb-3">每日 tokens</h2>
          <div v-if="!summary.by_day?.length" class="text-xs text-fg-tertiary py-6 text-center">
            本月還沒有用量
          </div>
          <div v-else class="space-y-1.5">
            <div v-for="d in summary.by_day" :key="d.day" class="flex items-center gap-3">
              <span class="text-[11px] w-20 text-fg-tertiary font-mono">{{ d.day }}</span>
              <div class="flex-1 bg-neutral-100 rounded h-4 overflow-hidden">
                <div class="bg-brand-500 h-full rounded transition-all"
                     :style="{ width: pct(d.tokens, maxDayTokens) + '%' }"></div>
              </div>
              <span class="text-[11px] w-24 text-right tabular-nums text-fg-secondary">
                {{ fmtNum(d.tokens) }}
              </span>
              <span class="text-[11px] w-20 text-right tabular-nums text-fg-tertiary">
                ${{ Number(d.cost_usd).toFixed(4) }}
              </span>
            </div>
          </div>
        </section>

        <!-- by_model table -->
        <section class="bg-surface-raised rounded-xl border border-neutral-200 overflow-hidden">
          <div class="px-5 py-3 border-b border-neutral-100">
            <h2 class="text-sm font-semibold text-fg">每模型用量</h2>
          </div>
          <table class="w-full text-sm">
            <thead class="bg-surface-sunken text-xs text-fg-tertiary uppercase">
              <tr>
                <th class="px-4 py-2 text-left font-medium">Model</th>
                <th class="px-4 py-2 text-right font-medium">Tokens</th>
                <th class="px-4 py-2 text-right font-medium">Cost (USD)</th>
                <th class="px-4 py-2 text-right font-medium">Requests</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!summary.by_model?.length">
                <td colspan="4" class="px-4 py-8 text-center text-xs text-fg-tertiary">
                  本月還沒有用量
                </td>
              </tr>
              <tr v-for="m in summary.by_model" :key="m.model"
                  class="border-t border-neutral-100 hover:bg-neutral-50/40 transition">
                <td class="px-4 py-2 text-xs text-fg font-mono">{{ m.model }}</td>
                <td class="px-4 py-2 text-xs text-right tabular-nums">{{ fmtNum(m.tokens) }}</td>
                <td class="px-4 py-2 text-xs text-right tabular-nums">${{ Number(m.cost_usd).toFixed(4) }}</td>
                <td class="px-4 py-2 text-xs text-right tabular-nums text-fg-tertiary">{{ fmtNum(m.requests) }}</td>
              </tr>
            </tbody>
          </table>
        </section>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { SIcon, SSpinner } from '@staffkm/ui-kit'
import { usageApi, type UsageSummary } from '../../api/usage'

const summary = ref<UsageSummary | null>(null)
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    summary.value = await usageApi.summary()
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '載入失敗')
  } finally {
    loading.value = false
  }
}

const maxDayTokens = computed(() => {
  const arr = summary.value?.by_day || []
  return arr.reduce((m, d) => Math.max(m, d.tokens), 0) || 1
})

// quota 剩餘 — token cap 優先；都沒設則 cost cap；都沒 → 「無上限」
const quotaRemainLabel = computed(() => {
  const s = summary.value
  if (!s) return '—'
  const tCap = s.quota.monthly_token_cap
  const cCap = s.quota.monthly_cost_cap_usd
  if (tCap) {
    const remain = Math.max(0, 100 - (s.usage.tokens / tCap) * 100)
    return remain.toFixed(0) + '%'
  }
  if (cCap) {
    const remain = Math.max(0, 100 - (s.usage.cost_usd / cCap) * 100)
    return remain.toFixed(0) + '%'
  }
  return '∞'
})

const quotaRemainColor = computed(() => {
  const s = summary.value
  if (!s) return 'text-fg'
  const tCap = s.quota.monthly_token_cap
  const cCap = s.quota.monthly_cost_cap_usd
  let used = 0
  if (tCap) used = (s.usage.tokens / tCap) * 100
  else if (cCap) used = (s.usage.cost_usd / cCap) * 100
  else return 'text-success-600'
  if (used >= 90) return 'text-danger-600'
  if (used >= 70) return 'text-warning-600'
  return 'text-success-600'
})

const quotaRemainHint = computed(() => {
  const s = summary.value
  if (!s) return ''
  if (s.quota.monthly_token_cap) return 'token 額度'
  if (s.quota.monthly_cost_cap_usd) return '成本額度'
  return '未設定上限'
})

function pct(v: number, max: number): number {
  if (!max) return 0
  return Math.max(2, (v / max) * 100)
}

function fmtNum(n: number | null | undefined): string {
  if (n === null || n === undefined) return '—'
  return Number(n).toLocaleString('zh-TW')
}

onMounted(load)
</script>
