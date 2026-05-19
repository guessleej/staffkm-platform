<template>
  <div class="flex-1 flex flex-col overflow-hidden">
    <div class="px-6 py-5 flex-shrink-0"><div class="card-hero flex items-center justify-between gap-4">
      <div>
        <h1 class="heading-page heading-accent">Token 用量 / Quota</h1>
        <p class="text-sm text-neutral-500 mt-0.5">當前 workspace 當月模型用量與額度設定</p>
      </div>
      <button
        @click="refresh"
        class="h-9 px-3 text-sm rounded-lg border border-neutral-200 hover:bg-neutral-50 transition"
        :aria-label="'重新整理用量資料'"
      >
        重新整理
      </button>
    </div>

</div>
    <div class="flex-1 overflow-y-auto p-6 space-y-6">
      <!-- 月度總覽卡（v2 SStatCard + SProgress）-->
      <section v-if="summary" aria-labelledby="usage-overview-h" class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <h2 id="usage-overview-h" class="sr-only">當月用量總覽</h2>

        <SStatCard
          :label="`本月（${summary.month}）總 token`"
          :value="summary.usage.tokens"
          format="number"
          icon="📊"
          :tone="tokenPct >= 90 ? 'danger' : tokenPct >= 70 ? 'warning' : 'brand'"
        >
          <template #footer>
            <div v-if="summary.quota.monthly_token_cap" class="mt-3">
              <div class="flex justify-between text-[11px] text-neutral-500 mb-1">
                <span>已用 / 上限</span><span>{{ Math.round(tokenPct) }}%</span>
              </div>
              <SProgress :value="tokenPct"
                         :tone="tokenPct >= 90 ? 'danger' : tokenPct >= 70 ? 'warning' : 'brand'"/>
            </div>
            <p v-else class="mt-3 text-[11px] text-neutral-400">未設定上限（無限制）</p>
          </template>
        </SStatCard>

        <SStatCard
          label="本月成本"
          :value="summary.usage.cost_usd"
          format="currency"
          icon="💵"
          :tone="costPct >= 90 ? 'danger' : costPct >= 70 ? 'warning' : 'success'"
        >
          <template #footer>
            <div v-if="summary.quota.monthly_cost_cap_usd" class="mt-3">
              <div class="flex justify-between text-[11px] text-neutral-500 mb-1">
                <span>已用 / 上限</span><span>{{ Math.round(costPct) }}%</span>
              </div>
              <SProgress :value="costPct"
                         :tone="costPct >= 90 ? 'danger' : costPct >= 70 ? 'warning' : 'success'"/>
            </div>
            <p v-else class="mt-3 text-[11px] text-neutral-400">未設定上限（無限制）</p>
          </template>
        </SStatCard>

        <SStatCard
          label="請求數"
          :value="summary.usage.requests"
          format="number"
          hint="本月（含 ok / error / client_disconnect）"
          icon="🔁"
          tone="neutral"
        />
      </section>

      <!-- Quota 設定 -->
      <section aria-labelledby="quota-h" class="card-warm p-5">
        <h2 id="quota-h" class="text-sm font-semibold text-neutral-900">Quota 設定</h2>
        <p class="text-xs text-neutral-500 mt-0.5">留空表示無上限；超過上限時新請求回 429。</p>
        <div class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label for="qt" class="block text-xs text-neutral-500 mb-1">月 token 上限</label>
            <input id="qt" v-model.number="quotaDraft.monthly_token_cap" type="number" min="0"
                   class="w-full h-9 px-3 text-sm rounded-md border border-neutral-200 focus:outline-none focus:ring-1 focus:ring-brand-400"
                   placeholder="不限"/>
          </div>
          <div>
            <label for="qc" class="block text-xs text-neutral-500 mb-1">月成本上限（USD）</label>
            <input id="qc" v-model.number="quotaDraft.monthly_cost_cap_usd" type="number" min="0" step="0.01"
                   class="w-full h-9 px-3 text-sm rounded-md border border-neutral-200 focus:outline-none focus:ring-1 focus:ring-brand-400"
                   placeholder="不限"/>
          </div>
        </div>
        <div class="mt-4 flex justify-end">
          <button
            @click="saveQuota"
            :disabled="savingQuota"
            class="h-9 px-4 text-sm rounded-lg bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-40"
          >
            {{ savingQuota ? '儲存中…' : '儲存 Quota' }}
          </button>
        </div>
      </section>

      <!-- 最近用量 -->
      <section aria-labelledby="logs-h" class="card-warm overflow-hidden">
        <div class="px-5 py-3 border-b border-neutral-100 flex items-center justify-between">
          <h2 id="logs-h" class="text-sm font-semibold text-neutral-900">最近用量（最多 50 筆）</h2>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-neutral-50 text-xs text-neutral-500 uppercase">
              <tr>
                <th class="px-4 py-2 text-left font-medium">時間</th>
                <th class="px-4 py-2 text-left font-medium">Provider · Model</th>
                <th class="px-4 py-2 text-right font-medium">in</th>
                <th class="px-4 py-2 text-right font-medium">out</th>
                <th class="px-4 py-2 text-right font-medium">total</th>
                <th class="px-4 py-2 text-right font-medium">cost (USD)</th>
                <th class="px-4 py-2 text-right font-medium">ms</th>
                <th class="px-4 py-2 text-left font-medium">狀態</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="logsLoading" >
                <td colspan="8" class="px-4 py-6 text-center text-xs text-neutral-400">載入中…</td>
              </tr>
              <tr v-else-if="!logs.length">
                <td colspan="8" class="px-4 py-10 text-center text-xs text-neutral-400">尚無用量紀錄</td>
              </tr>
              <tr v-for="l in logs" :key="l.id" class="border-t border-neutral-100">
                <td class="px-4 py-2 text-xs text-neutral-500 font-mono whitespace-nowrap">{{ formatTime(l.created_at) }}</td>
                <td class="px-4 py-2 text-xs text-neutral-700">
                  <span class="font-mono text-neutral-500">{{ l.provider_type || '-' }}</span>
                  <span class="mx-1 text-neutral-300">·</span>
                  <span>{{ l.model || '-' }}</span>
                </td>
                <td class="px-4 py-2 text-xs text-right tabular-nums">{{ fmt(l.prompt_tokens) }}</td>
                <td class="px-4 py-2 text-xs text-right tabular-nums">{{ fmt(l.completion_tokens) }}</td>
                <td class="px-4 py-2 text-xs text-right tabular-nums font-medium">{{ fmt(l.total_tokens) }}</td>
                <td class="px-4 py-2 text-xs text-right tabular-nums">{{ Number(l.cost_usd).toFixed(4) }}</td>
                <td class="px-4 py-2 text-xs text-right tabular-nums text-neutral-500">{{ l.latency_ms }}</td>
                <td class="px-4 py-2 text-xs">
                  <span class="inline-block px-2 py-0.5 rounded-full text-[10px]"
                        :class="statusBadge(l.status)">{{ l.status }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { usageApi, type UsageSummary, type UsageLog } from '../../api/usage'
import { useToast } from '../../composables/useToast'
import { SStatCard, SProgress } from '@staffkm/ui-kit'

const toast = useToast()

const summary = ref<UsageSummary | null>(null)
const logs = ref<UsageLog[]>([])
const logsLoading = ref(false)
const savingQuota = ref(false)

const quotaDraft = reactive<{ monthly_token_cap: number | null; monthly_cost_cap_usd: number | null }>({
  monthly_token_cap: null,
  monthly_cost_cap_usd: null,
})

const tokenPct = computed(() => {
  if (!summary.value?.quota.monthly_token_cap) return 0
  return (summary.value.usage.tokens / summary.value.quota.monthly_token_cap) * 100
})
const costPct = computed(() => {
  if (!summary.value?.quota.monthly_cost_cap_usd) return 0
  return (summary.value.usage.cost_usd / summary.value.quota.monthly_cost_cap_usd) * 100
})

async function loadSummary() {
  try {
    summary.value = await usageApi.summary()
    quotaDraft.monthly_token_cap = summary.value.quota.monthly_token_cap
    quotaDraft.monthly_cost_cap_usd = summary.value.quota.monthly_cost_cap_usd
  } catch (e: any) {
    toast.error('讀取用量失敗：' + (e?.message || e))
  }
}

async function loadLogs() {
  logsLoading.value = true
  try {
    const r = await usageApi.logs(1, 50)
    logs.value = r.items
  } catch (e: any) {
    toast.error('讀取紀錄失敗：' + (e?.message || e))
  } finally {
    logsLoading.value = false
  }
}

async function refresh() {
  await Promise.all([loadSummary(), loadLogs()])
  toast.success('已重新整理')
}

async function saveQuota() {
  savingQuota.value = true
  try {
    await usageApi.setQuota({
      monthly_token_cap: quotaDraft.monthly_token_cap || null,
      monthly_cost_cap_usd: quotaDraft.monthly_cost_cap_usd || null,
    })
    toast.success('Quota 已更新')
    await loadSummary()
  } catch (e: any) {
    toast.error('儲存失敗：' + (e?.message || e))
  } finally {
    savingQuota.value = false
  }
}

function fmt(n: number) {
  return n.toLocaleString('zh-TW')
}
function formatTime(s: string) {
  try { return new Date(s).toLocaleString('zh-TW', { hour12: false }) }
  catch { return s }
}
function statusBadge(s: string) {
  return {
    ok:                'bg-success-50 text-success-700',
    error:             'bg-danger-50 text-danger-700',
    client_disconnect: 'bg-neutral-100 text-neutral-600',
  }[s] || 'bg-neutral-100 text-neutral-600'
}

onMounted(async () => {
  await Promise.all([loadSummary(), loadLogs()])
})
</script>
