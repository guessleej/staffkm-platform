<template>
  <div class="flex flex-col h-full">
    <!-- 頁首 -->
    <div class="bg-surface-raised border-b border-neutral-200 px-6 py-4 flex items-center justify-between flex-shrink-0">
      <div>
        <h1 class="text-lg font-semibold text-fg">使用者用量 / 配額</h1>
        <p class="text-sm text-fg-tertiary mt-0.5">設定每位使用者本月 token / cost 上限</p>
      </div>
      <button
        @click="load"
        class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50 transition flex items-center gap-1"
      >
        <SIcon name="refresh" :size="12" /> 重新整理
      </button>
    </div>

    <!-- table -->
    <div class="flex-1 overflow-y-auto p-6">
      <div v-if="loading" class="flex justify-center py-20">
        <SSpinner :size="24" />
      </div>

      <div v-else-if="!rows.length" class="text-center py-20">
        <div class="w-12 h-12 bg-brand-50 rounded-2xl flex items-center justify-center mx-auto mb-3">
          <SIcon name="user" :size="24" :stroke-width="1.5" class="text-brand-500" />
        </div>
        <p class="text-fg-secondary font-medium">沒有使用者</p>
      </div>

      <table v-else class="w-full text-sm bg-surface-raised border border-neutral-200 rounded-xl overflow-hidden">
        <thead>
          <tr class="bg-surface-sunken text-xs uppercase tracking-wider text-fg-tertiary text-left">
            <th class="px-4 py-3 font-semibold">使用者</th>
            <th class="px-4 py-3 font-semibold w-[28%]">Tokens (本月 used / cap)</th>
            <th class="px-4 py-3 font-semibold w-[28%]">Cost USD (本月 used / cap)</th>
            <th class="px-4 py-3 font-semibold text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.user_id"
              class="border-t border-neutral-100 hover:bg-neutral-50/40 transition">
            <td class="px-4 py-3">
              <p class="font-medium text-fg text-sm">{{ r.username }}</p>
              <p class="text-[11px] text-fg-tertiary mt-0.5">{{ r.email }}</p>
            </td>
            <td class="px-4 py-3">
              <UsageBar :used="r.tokens_used" :cap="r.monthly_token_cap" />
            </td>
            <td class="px-4 py-3">
              <UsageBar :used="r.cost_used" :cap="r.monthly_cost_cap_usd" :format-as-cost="true" />
            </td>
            <td class="px-4 py-3 text-right">
              <button
                @click="openEdit(r)"
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
      <div class="bg-surface-raised rounded-xl border border-neutral-200 shadow-xl w-full max-w-md p-5">
        <h3 class="text-base font-semibold text-fg">設定 Quota</h3>
        <p class="text-xs text-fg-tertiary mt-0.5">{{ editing.username }} · {{ editing.email }}</p>

        <div class="mt-4 space-y-3">
          <div>
            <label class="block text-xs text-fg-secondary mb-1">月 token 上限</label>
            <input
              v-model.number="draft.monthly_token_cap"
              type="number" min="0"
              class="w-full h-9 px-3 text-sm rounded-md border border-neutral-200 focus:outline-none focus:ring-1 focus:ring-brand-400 bg-surface-raised text-fg"
              placeholder="留空 = 不限"
            />
          </div>
          <div>
            <label class="block text-xs text-fg-secondary mb-1">月成本上限（USD）</label>
            <input
              v-model.number="draft.monthly_cost_cap_usd"
              type="number" min="0" step="0.01"
              class="w-full h-9 px-3 text-sm rounded-md border border-neutral-200 focus:outline-none focus:ring-1 focus:ring-brand-400 bg-surface-raised text-fg"
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
import { userQuotaApi, type UserQuotaRow } from '../../api/userQuota'
import UsageBar from './UsageBar.vue'

const rows    = ref<UserQuotaRow[]>([])
const loading = ref(true)
const editing = ref<UserQuotaRow | null>(null)
const saving  = ref(false)

const draft = reactive<{ monthly_token_cap: number | null; monthly_cost_cap_usd: number | null }>({
  monthly_token_cap:    null,
  monthly_cost_cap_usd: null,
})

async function load() {
  loading.value = true
  try {
    const r = await userQuotaApi.list()
    rows.value = r.items
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '載入失敗')
  } finally {
    loading.value = false
  }
}

function openEdit(r: UserQuotaRow) {
  editing.value = r
  draft.monthly_token_cap    = r.monthly_token_cap
  draft.monthly_cost_cap_usd = r.monthly_cost_cap_usd
}

function closeEdit() {
  editing.value = null
}

async function saveEdit() {
  if (!editing.value) return
  saving.value = true
  try {
    await userQuotaApi.update(editing.value.user_id, {
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

onMounted(load)
</script>
