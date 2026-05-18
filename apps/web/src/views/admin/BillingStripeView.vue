<template>
  <div class="flex flex-col h-full">
    <!-- 頁首 -->
    <div class="bg-surface-raised border-b border-neutral-200 px-6 py-4 flex items-center justify-between flex-shrink-0">
      <div>
        <h1 class="text-lg font-semibold text-fg">Stripe Billing</h1>
        <p class="text-sm text-fg-tertiary mt-0.5">訂閱 / 預付額度 / 發票（v4.7 + v4.8）</p>
      </div>
      <button
        @click="reload"
        class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50 transition flex items-center gap-1"
      >
        <SIcon name="refresh" :size="12" /> 重新整理
      </button>
    </div>

    <div class="flex-1 overflow-auto px-6 py-6 space-y-6">
      <!-- 當前方案卡片 -->
      <section class="bg-surface-raised border border-neutral-200 rounded-xl p-5">
        <h2 class="text-sm font-medium text-fg mb-3">目前方案</h2>
        <div v-if="loading" class="text-sm text-fg-tertiary">載入中…</div>
        <div v-else-if="me" class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <div class="text-xs text-fg-tertiary">Plan</div>
            <div class="text-base font-semibold text-fg mt-1">{{ planLabel(me.plan) }}</div>
          </div>
          <div>
            <div class="text-xs text-fg-tertiary">Status</div>
            <div class="text-base font-semibold text-fg mt-1">{{ me.status }}</div>
          </div>
          <div>
            <div class="text-xs text-fg-tertiary">Credits Balance</div>
            <div class="text-base font-semibold text-fg mt-1">${{ me.credits_balance.toFixed(4) }}</div>
          </div>
          <div>
            <div class="text-xs text-fg-tertiary">當期</div>
            <div class="text-xs text-fg mt-1">
              {{ fmtDate(me.current_period_start) }} → {{ fmtDate(me.current_period_end) }}
            </div>
          </div>
        </div>
        <div class="mt-4 flex flex-wrap gap-2">
          <button
            v-for="p in subscribePlans"
            :key="p.code"
            @click="checkout(p.code)"
            :disabled="busy"
            class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50 transition"
          >
            升級 {{ p.label }}
          </button>
          <button
            v-for="t in topupPlans"
            :key="t.code"
            @click="checkout(t.code)"
            :disabled="busy"
            class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50 transition"
          >
            加值 {{ t.label }}
          </button>
          <button
            @click="openPortal"
            :disabled="busy"
            class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50 transition flex items-center gap-1"
          >
            <SIcon name="settings" :size="12" /> 管理訂閱
          </button>
        </div>
        <p v-if="err" class="text-xs text-warning-600 mt-3">{{ err }}</p>
      </section>

      <!-- 發票 -->
      <section class="bg-surface-raised border border-neutral-200 rounded-xl p-5">
        <h2 class="text-sm font-medium text-fg mb-3">發票紀錄</h2>
        <div v-if="invoices.length === 0" class="text-sm text-fg-tertiary">尚無發票</div>
        <table v-else class="w-full text-xs">
          <thead class="text-fg-tertiary">
            <tr class="border-b border-neutral-200">
              <th class="text-left py-2">日期</th>
              <th class="text-left py-2">金額</th>
              <th class="text-left py-2">狀態</th>
              <th class="text-left py-2">期間</th>
              <th class="text-left py-2">PDF</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="inv in invoices" :key="inv.id" class="border-b border-neutral-100">
              <td class="py-2 text-fg">{{ fmtDate(inv.created_at) }}</td>
              <td class="py-2 text-fg">${{ inv.amount_usd.toFixed(2) }} {{ inv.currency.toUpperCase() }}</td>
              <td class="py-2 text-fg-secondary">{{ inv.status }}</td>
              <td class="py-2 text-fg-secondary">{{ fmtDate(inv.period_start) }} → {{ fmtDate(inv.period_end) }}</td>
              <td class="py-2">
                <a v-if="inv.invoice_pdf_url" :href="inv.invoice_pdf_url" target="_blank"
                   class="text-brand-600 hover:underline">下載</a>
                <span v-else class="text-fg-tertiary">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- Credit Ledger（可摺疊） -->
      <section class="bg-surface-raised border border-neutral-200 rounded-xl p-5">
        <button
          @click="showLedger = !showLedger"
          class="w-full flex items-center justify-between text-sm font-medium text-fg"
        >
          <span>額度交易紀錄（{{ ledger.length }}）</span>
          <SIcon :name="showLedger ? 'chevron-up' : 'chevron-down'" :size="14" />
        </button>
        <div v-if="showLedger" class="mt-3">
          <div v-if="ledger.length === 0" class="text-sm text-fg-tertiary">無紀錄</div>
          <table v-else class="w-full text-xs">
            <thead class="text-fg-tertiary">
              <tr class="border-b border-neutral-200">
                <th class="text-left py-2">時間</th>
                <th class="text-left py-2">事由</th>
                <th class="text-right py-2">變動</th>
                <th class="text-right py-2">餘額</th>
                <th class="text-left py-2 pl-3">Ref</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(e, i) in ledger" :key="i" class="border-b border-neutral-100">
                <td class="py-2 text-fg">{{ fmtDate(e.created_at) }}</td>
                <td class="py-2 text-fg-secondary">{{ e.reason }}</td>
                <td class="py-2 text-right" :class="e.delta_usd >= 0 ? 'text-success-600' : 'text-warning-600'">
                  {{ e.delta_usd >= 0 ? '+' : '' }}${{ e.delta_usd.toFixed(4) }}
                </td>
                <td class="py-2 text-right text-fg">${{ e.balance_after.toFixed(4) }}</td>
                <td class="py-2 pl-3 text-fg-tertiary truncate max-w-[16ch]">{{ e.reference || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { SIcon } from '@staffkm/ui-kit'
import { billingApi, type BillingMe, type BillingInvoice, type CreditLedgerEntry } from '../../api/billing'

const loading = ref(true)
const busy = ref(false)
const err = ref('')
const me = ref<BillingMe | null>(null)
const invoices = ref<BillingInvoice[]>([])
const ledger = ref<CreditLedgerEntry[]>([])
const showLedger = ref(false)

const subscribePlans = [
  { code: 'starter', label: 'Starter ($29/mo)' },
  { code: 'pro',     label: 'Pro ($199/mo)' },
  { code: 'usage',   label: 'Metered Usage' },
]
const topupPlans = [
  { code: 'topup10',  label: '$10' },
  { code: 'topup50',  label: '$50' },
  { code: 'topup200', label: '$200' },
]

function planLabel(p: string): string {
  return ({ trial: 'Trial', starter: 'Starter', pro: 'Pro', usage: 'Metered Usage' } as Record<string, string>)[p] || p
}
function fmtDate(s: string | null): string {
  if (!s) return '—'
  try { return new Date(s).toLocaleDateString() } catch { return s }
}

async function reload() {
  loading.value = true
  err.value = ''
  try {
    me.value = await billingApi.me()
    invoices.value = (await billingApi.invoices()).items
    ledger.value = (await billingApi.ledger()).items
  } catch (e: any) {
    err.value = e?.response?.data?.detail || e?.message || 'load failed'
  } finally {
    loading.value = false
  }
}

async function checkout(plan: string) {
  busy.value = true
  err.value = ''
  try {
    const { checkout_url } = await billingApi.checkout(plan)
    window.location.href = checkout_url
  } catch (e: any) {
    err.value = e?.response?.data?.detail || e?.message || 'checkout failed'
  } finally {
    busy.value = false
  }
}

async function openPortal() {
  busy.value = true
  err.value = ''
  try {
    const { portal_url } = await billingApi.portal()
    window.location.href = portal_url
  } catch (e: any) {
    err.value = e?.response?.data?.detail || e?.message || 'portal failed'
  } finally {
    busy.value = false
  }
}

onMounted(reload)
</script>
