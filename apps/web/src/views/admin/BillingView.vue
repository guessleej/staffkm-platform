<template>
  <div class="flex flex-col h-full">
    <!-- 頁首 -->
    <div class="bg-surface-raised border-b border-neutral-200 px-6 py-4 flex items-center justify-between flex-shrink-0">
      <div>
        <h1 class="text-lg font-semibold text-fg">Per-User Billing</h1>
        <p class="text-sm text-fg-tertiary mt-0.5">跨 workspace 真實用量報表（v3.8 P2）</p>
      </div>
      <div class="flex items-center gap-2">
        <select
          v-model="month"
          @change="load"
          class="px-3 py-1.5 text-xs text-fg bg-surface-raised border border-neutral-200 rounded-lg"
        >
          <option v-for="m in monthOptions" :key="m" :value="m">{{ m }}</option>
        </select>
        <a
          :href="csvHref"
          target="_blank"
          class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50 transition flex items-center gap-1"
        >
          <SIcon name="download" :size="12" /> 匯出 CSV
        </a>
        <button
          @click="load"
          class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50 transition flex items-center gap-1"
        >
          <SIcon name="refresh" :size="12" /> 重新整理
        </button>
      </div>
    </div>

    <!-- summary card -->
    <div class="px-6 pt-6">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="bg-surface-raised border border-neutral-200 rounded-xl p-4">
          <div class="text-xs text-fg-tertiary uppercase tracking-wider">總成本（USD）</div>
          <div class="text-2xl font-semibold text-fg mt-1">${{ fmtMoney(summary.total_cost) }}</div>
        </div>
        <div class="bg-surface-raised border border-neutral-200 rounded-xl p-4">
          <div class="text-xs text-fg-tertiary uppercase tracking-wider">總 Tokens</div>
          <div class="text-2xl font-semibold text-fg mt-1">{{ fmtNum(summary.total_tokens) }}</div>
        </div>
        <div class="bg-surface-raised border border-neutral-200 rounded-xl p-4">
          <div class="text-xs text-fg-tertiary uppercase tracking-wider">活躍使用者</div>
          <div class="text-2xl font-semibold text-fg mt-1">{{ summary.user_count }}</div>
        </div>
      </div>
    </div>

    <!-- table -->
    <div class="flex-1 overflow-y-auto p-6">
      <div v-if="loading && !items.length" class="flex justify-center py-20">
        <SSpinner :size="24" />
      </div>

      <div v-else-if="!items.length" class="text-center py-20">
        <div class="w-12 h-12 bg-brand-50 rounded-2xl flex items-center justify-center mx-auto mb-3">
          <SIcon name="file-text" :size="24" :stroke-width="1.5" class="text-brand-500" />
        </div>
        <p class="text-fg-secondary font-medium">本月尚無計費紀錄</p>
        <p class="text-xs text-fg-tertiary mt-1">當有使用者呼叫模型後會出現在此</p>
      </div>

      <table v-else class="w-full text-sm bg-surface-raised border border-neutral-200 rounded-xl overflow-hidden">
        <thead>
          <tr class="bg-surface-sunken text-xs uppercase tracking-wider text-fg-tertiary text-left">
            <th class="px-4 py-3 font-semibold">使用者</th>
            <th class="px-4 py-3 font-semibold">Email</th>
            <th class="px-4 py-3 font-semibold">Workspace</th>
            <th class="px-4 py-3 font-semibold text-right">Calls</th>
            <th class="px-4 py-3 font-semibold text-right">Tokens</th>
            <th class="px-4 py-3 font-semibold text-right">Cost (USD)</th>
            <th class="px-4 py-3 font-semibold text-right">會話數</th>
            <th class="px-4 py-3 font-semibold text-center">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in items"
            :key="row.user_id + row.workspace_id"
            class="border-t border-neutral-100 hover:bg-neutral-50/40 transition cursor-pointer"
            @click="openDetail(row)"
          >
            <td class="px-4 py-3 text-fg font-medium">{{ formatUserName(row) }}</td>
            <td class="px-4 py-3 text-fg-secondary text-xs">{{ row.email }}</td>
            <td class="px-4 py-3 text-fg-secondary text-xs">{{ row.workspace_name || '—' }}</td>
            <td class="px-4 py-3 text-right text-fg-secondary">{{ fmtNum(row.calls) }}</td>
            <td class="px-4 py-3 text-right text-fg-secondary">{{ fmtNum(row.tokens) }}</td>
            <td class="px-4 py-3 text-right text-fg font-semibold">${{ fmtMoney(row.cost) }}</td>
            <td class="px-4 py-3 text-right text-fg-secondary">{{ row.conversations }}</td>
            <td class="px-4 py-3 text-center">
              <button
                @click.stop="openDetail(row)"
                class="text-xs text-brand-600 hover:text-brand-700 inline-flex items-center gap-1"
              >
                <SIcon name="eye" :size="12" /> 詳情
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 詳情抽屜 -->
    <transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0"
      leave-active-class="transition duration-150 ease-in"
      leave-to-class="opacity-0"
    >
      <div
        v-if="selected"
        class="fixed inset-0 bg-black/30 z-40 flex justify-end"
        @click.self="closeDetail"
      >
        <div class="w-full max-w-2xl bg-surface-raised h-full overflow-y-auto shadow-xl">
          <div class="px-6 py-4 border-b border-neutral-200 flex items-center justify-between sticky top-0 bg-surface-raised z-10">
            <div>
              <h2 class="text-base font-semibold text-fg">{{ formatUserName(selected) }}</h2>
              <p class="text-xs text-fg-tertiary mt-0.5">{{ selected.email }} · {{ selected.workspace_name || '—' }}</p>
            </div>
            <button
              @click="closeDetail"
              class="p-1.5 text-fg-tertiary hover:text-fg hover:bg-neutral-100 rounded-lg"
            >
              <SIcon name="x" :size="16" />
            </button>
          </div>

          <div v-if="detailLoading" class="flex justify-center py-20">
            <SSpinner :size="24" />
          </div>

          <div v-else-if="detail" class="px-6 py-5 space-y-8">
            <!-- by feature -->
            <section>
              <h3 class="text-sm font-semibold text-fg mb-3 flex items-center gap-1.5">
                <SIcon name="filter" :size="14" /> 依功能拆分
              </h3>
              <div v-if="!detail.by_feature.length" class="text-xs text-fg-tertiary">無資料</div>
              <table v-else class="w-full text-sm border border-neutral-200 rounded-lg overflow-hidden">
                <thead>
                  <tr class="bg-surface-sunken text-xs uppercase tracking-wider text-fg-tertiary text-left">
                    <th class="px-3 py-2 font-semibold">Feature</th>
                    <th class="px-3 py-2 font-semibold text-right">Calls</th>
                    <th class="px-3 py-2 font-semibold text-right">Tokens</th>
                    <th class="px-3 py-2 font-semibold text-right">Cost</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(f, i) in detail.by_feature" :key="f.feature" class="border-t border-neutral-100">
                    <td class="px-3 py-2">
                      <span
                        class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs"
                        :class="featureColor(i)"
                      >
                        {{ f.feature }}
                      </span>
                    </td>
                    <td class="px-3 py-2 text-right text-fg-secondary text-xs">{{ fmtNum(f.calls) }}</td>
                    <td class="px-3 py-2 text-right text-fg-secondary text-xs">{{ fmtNum(f.tokens) }}</td>
                    <td class="px-3 py-2 text-right text-fg font-semibold text-xs">${{ fmtMoney(f.cost) }}</td>
                  </tr>
                </tbody>
              </table>
            </section>

            <!-- top conversations -->
            <section>
              <h3 class="text-sm font-semibold text-fg mb-3 flex items-center gap-1.5">
                <SIcon name="message-square" :size="14" /> 最高成本會話 Top 20
              </h3>
              <div v-if="!detail.top_conversations.length" class="text-xs text-fg-tertiary">無資料</div>
              <table v-else class="w-full text-sm border border-neutral-200 rounded-lg overflow-hidden">
                <thead>
                  <tr class="bg-surface-sunken text-xs uppercase tracking-wider text-fg-tertiary text-left">
                    <th class="px-3 py-2 font-semibold">Conversation</th>
                    <th class="px-3 py-2 font-semibold text-right">Calls</th>
                    <th class="px-3 py-2 font-semibold text-right">Tokens</th>
                    <th class="px-3 py-2 font-semibold text-right">Cost</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="c in detail.top_conversations" :key="c.conversation_id" class="border-t border-neutral-100">
                    <td class="px-3 py-2 font-mono text-[11px] text-fg-secondary truncate max-w-[180px]">{{ c.conversation_id }}</td>
                    <td class="px-3 py-2 text-right text-fg-secondary text-xs">{{ fmtNum(c.calls) }}</td>
                    <td class="px-3 py-2 text-right text-fg-secondary text-xs">{{ fmtNum(c.tokens) }}</td>
                    <td class="px-3 py-2 text-right text-fg font-semibold text-xs">${{ fmtMoney(c.cost) }}</td>
                  </tr>
                </tbody>
              </table>
            </section>

            <!-- daily bar chart -->
            <section>
              <h3 class="text-sm font-semibold text-fg mb-3 flex items-center gap-1.5">
                <SIcon name="play" :size="14" /> 每日趨勢
              </h3>
              <div v-if="!detail.daily.length" class="text-xs text-fg-tertiary">無資料</div>
              <div v-else class="border border-neutral-200 rounded-lg p-4">
                <div class="flex items-end gap-1 h-32">
                  <div
                    v-for="d in detail.daily"
                    :key="d.day"
                    class="flex-1 flex flex-col items-center justify-end group relative"
                  >
                    <div
                      class="w-full bg-brand-500 rounded-t transition hover:bg-brand-600"
                      :style="{ height: barHeight(d.cost) + '%' }"
                      :title="`${d.day}: $${fmtMoney(d.cost)} · ${fmtNum(d.tokens)} tokens`"
                    ></div>
                  </div>
                </div>
                <div class="flex justify-between text-[10px] text-fg-tertiary mt-2">
                  <span>{{ detail.daily[0]?.day }}</span>
                  <span>{{ detail.daily[detail.daily.length - 1]?.day }}</span>
                </div>
              </div>
            </section>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { SIcon, SSpinner } from '@staffkm/ui-kit'
import { adminBillingApi, type UserBillingRow, type UserBillingDetail, type UserBillingSummary } from '../../api/adminBilling'
import { formatUserName } from '../../utils/userName'

const items = ref<UserBillingRow[]>([])
const summary = ref<UserBillingSummary>({ total_cost: 0, total_tokens: 0, user_count: 0 })
const loading = ref(false)
const selected = ref<UserBillingRow | null>(null)
const detail = ref<UserBillingDetail | null>(null)
const detailLoading = ref(false)

const monthOptions = computed(() => {
  const now = new Date()
  return Array.from({ length: 6 }, (_, i) => {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
  })
})

const month = ref(monthOptions.value[0])

const csvHref = computed(() => adminBillingApi.csvUrl(month.value))

async function load() {
  loading.value = true
  try {
    const res = await adminBillingApi.list(month.value)
    items.value = res.items || []
    summary.value = res.summary || { total_cost: 0, total_tokens: 0, user_count: 0 }
  } catch (e) {
    console.warn('admin_billing_load_failed', e)
  } finally {
    loading.value = false
  }
}

async function openDetail(row: UserBillingRow) {
  selected.value = row
  detail.value = null
  detailLoading.value = true
  try {
    detail.value = await adminBillingApi.detail(row.user_id, month.value)
  } catch (e) {
    console.warn('admin_billing_detail_failed', e)
  } finally {
    detailLoading.value = false
  }
}

function closeDetail() {
  selected.value = null
  detail.value = null
}

function fmtMoney(v: number | null | undefined): string {
  const n = Number(v || 0)
  return n.toFixed(4)
}

function fmtNum(v: number | null | undefined): string {
  return (Number(v || 0)).toLocaleString('en-US')
}

const FEATURE_COLORS = [
  'bg-brand-50 text-brand-700',
  'bg-success-50 text-success-700',
  'bg-warning-50 text-warning-700',
  'bg-danger-50 text-danger-700',
  'bg-neutral-100 text-fg-secondary',
]
function featureColor(i: number): string {
  return FEATURE_COLORS[i % FEATURE_COLORS.length]
}

const maxDailyCost = computed(() => {
  if (!detail.value?.daily.length) return 1
  return Math.max(...detail.value.daily.map(d => d.cost), 0.0001)
})

function barHeight(cost: number): number {
  return Math.max(2, Math.round((cost / maxDailyCost.value) * 100))
}

onMounted(load)
</script>
