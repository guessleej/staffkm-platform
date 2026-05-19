<template>
  <div class="flex flex-col h-full">
    <!-- 頁首 -->
    <div class="px-6 py-5 flex-shrink-0"><div class="card-hero flex items-center justify-between gap-4">
      <div>
        <h1 class="heading-page heading-accent">Workspace Quota 管理</h1>
        <p class="text-sm text-fg-tertiary mt-0.5">跨 workspace 的當月用量與額度（{{ month || '—' }}）</p>
      </div>
      <button
        @click="load"
        class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50 transition flex items-center gap-1"
      >
        <SIcon name="refresh" :size="12" /> 重新整理
      </button>
    </div>

    <!-- table -->
</div>
    <div class="flex-1 overflow-y-auto p-6">
      <div v-if="loading" class="flex justify-center py-20">
        <SSpinner :size="24" />
      </div>

      <div v-else-if="!items.length" class="text-center py-20">
        <div class="w-12 h-12 bg-brand-50 rounded-2xl flex items-center justify-center mx-auto mb-3">
          <SIcon name="database" :size="24" :stroke-width="1.5" class="text-brand-500" />
        </div>
        <p class="text-fg-secondary font-medium">沒有 workspace</p>
      </div>

      <table v-else class="w-full text-sm bg-surface-raised border border-bd rounded-2xl overflow-hidden shadow-sm">
        <thead>
          <tr class="bg-surface-sunken text-xs uppercase tracking-wider text-fg-tertiary text-left">
            <th class="px-4 py-3 font-semibold">Workspace</th>
            <th class="px-4 py-3 font-semibold w-[28%]">Tokens (本月 used / cap)</th>
            <th class="px-4 py-3 font-semibold w-[28%]">Cost USD (本月 used / cap)</th>
            <th class="px-4 py-3 font-semibold text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in items" :key="row.workspace_id"
              class="border-t border-neutral-100 hover:bg-neutral-50/40 transition">
            <td class="px-4 py-3">
              <p class="font-medium text-fg text-sm">{{ row.workspace_name }}</p>
              <p class="text-[10px] text-fg-tertiary font-mono mt-0.5">{{ row.workspace_id }}</p>
            </td>

            <td class="px-4 py-3">
              <div class="flex items-center justify-between text-xs mb-1">
                <span class="font-mono tabular-nums text-fg">{{ fmtNum(row.tokens_used) }}</span>
                <span class="text-fg-tertiary">
                  / {{ row.monthly_token_cap === null ? '∞' : fmtNum(row.monthly_token_cap) }}
                </span>
              </div>
              <div class="h-1.5 w-full rounded-full bg-neutral-100 overflow-hidden">
                <div class="h-full rounded-full transition-all"
                     :class="barColor(pct(row.tokens_used, row.monthly_token_cap))"
                     :style="{ width: Math.min(100, pct(row.tokens_used, row.monthly_token_cap)) + '%' }"></div>
              </div>
            </td>

            <td class="px-4 py-3">
              <div class="flex items-center justify-between text-xs mb-1">
                <span class="font-mono tabular-nums text-fg">${{ Number(row.cost_used).toFixed(4) }}</span>
                <span class="text-fg-tertiary">
                  / {{ row.monthly_cost_cap_usd === null ? '∞' : '$' + Number(row.monthly_cost_cap_usd).toFixed(2) }}
                </span>
              </div>
              <div class="h-1.5 w-full rounded-full bg-neutral-100 overflow-hidden">
                <div class="h-full rounded-full transition-all"
                     :class="barColor(pct(row.cost_used, row.monthly_cost_cap_usd))"
                     :style="{ width: Math.min(100, pct(row.cost_used, row.monthly_cost_cap_usd)) + '%' }"></div>
              </div>
            </td>

            <td class="px-4 py-3 text-right">
              <button
                @click="openEdit(row)"
                class="px-3 py-1 text-xs text-brand-700 bg-brand-50 hover:bg-brand-100 rounded-md transition"
              >設定</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal -->
    <div v-if="editing" class="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40"
         @click.self="closeEdit">
      <div class="card-warm shadow-xl w-full max-w-md p-5">
        <h3 class="text-base font-semibold text-fg">設定 Quota</h3>
        <p class="text-xs text-fg-tertiary mt-0.5">{{ editing.workspace_name }}</p>

        <div class="mt-4 space-y-3">
          <div>
            <label class="block text-xs text-fg-secondary mb-1">月 token 上限</label>
            <input
              v-model.number="draft.monthly_token_cap"
              type="number" min="0"
              class="form-input"
              placeholder="留空 = 不限"
            />
          </div>
          <div>
            <label class="block text-xs text-fg-secondary mb-1">月成本上限（USD）</label>
            <input
              v-model.number="draft.monthly_cost_cap_usd"
              type="number" min="0" step="0.01"
              class="form-input"
              placeholder="留空 = 不限"
            />
          </div>
        </div>

        <div class="mt-5 flex justify-end gap-2">
          <button
            @click="closeEdit"
            class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50"
          >取消</button>
          <button
            @click="saveEdit"
            :disabled="saving"
            class="px-3 py-1.5 text-xs text-white bg-brand-600 hover:bg-brand-700 rounded-lg disabled:opacity-50"
          >{{ saving ? '儲存中…' : '儲存' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { SIcon, SSpinner } from '@staffkm/ui-kit'
import { adminQuotaApi, type WorkspaceQuotaRow } from '../../api/adminQuota'

const items   = ref<WorkspaceQuotaRow[]>([])
const month   = ref<string>('')
const loading = ref(true)
const editing = ref<WorkspaceQuotaRow | null>(null)
const saving  = ref(false)

const draft = reactive<{ monthly_token_cap: number | null; monthly_cost_cap_usd: number | null }>({
  monthly_token_cap:    null,
  monthly_cost_cap_usd: null,
})

async function load() {
  loading.value = true
  try {
    const r = await adminQuotaApi.list()
    items.value = r.items
    month.value = r.month
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '載入失敗')
  } finally {
    loading.value = false
  }
}

function openEdit(row: WorkspaceQuotaRow) {
  editing.value = row
  draft.monthly_token_cap    = row.monthly_token_cap
  draft.monthly_cost_cap_usd = row.monthly_cost_cap_usd
}

function closeEdit() {
  editing.value = null
}

async function saveEdit() {
  if (!editing.value) return
  saving.value = true
  try {
    await adminQuotaApi.update(editing.value.workspace_id, {
      monthly_token_cap:    draft.monthly_token_cap    || null,
      monthly_cost_cap_usd: draft.monthly_cost_cap_usd || null,
    })
    closeEdit()
    await load()
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '儲存失敗')
  } finally {
    saving.value = false
  }
}

function pct(used: number, cap: number | null): number {
  if (!cap || cap <= 0) return 0
  return (Number(used) / Number(cap)) * 100
}

function barColor(p: number): string {
  if (p >= 90) return 'bg-danger-500'
  if (p >= 70) return 'bg-warning-500'
  return 'bg-success-500'
}

function fmtNum(n: number | null | undefined): string {
  if (n === null || n === undefined) return '—'
  return Number(n).toLocaleString('zh-TW')
}

onMounted(load)
</script>
