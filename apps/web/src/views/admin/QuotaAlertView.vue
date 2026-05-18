<template>
  <div class="flex flex-col h-full">
    <!-- 頁首 -->
    <div class="bg-surface-raised border-b border-neutral-200 px-6 py-4 flex items-center justify-between flex-shrink-0">
      <div>
        <h1 class="text-lg font-semibold text-fg">配額告警</h1>
        <p class="text-sm text-fg-tertiary mt-0.5">設定 workspace / user 用量達閾值時的通知規則</p>
      </div>
      <div class="flex items-center gap-2">
        <button
          @click="load"
          class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50 transition flex items-center gap-1"
        >
          <SIcon name="refresh" :size="12" /> 重新整理
        </button>
        <button
          @click="openCreate"
          class="px-3 py-1.5 text-xs text-white bg-brand-600 hover:bg-brand-700 rounded-lg transition flex items-center gap-1"
        >
          <SIcon name="plus" :size="12" /> 新增 alert
        </button>
      </div>
    </div>

    <!-- table -->
    <div class="flex-1 overflow-y-auto p-6">
      <div v-if="loading" class="flex justify-center py-20">
        <SSpinner :size="24" />
      </div>

      <div v-else-if="!items.length" class="text-center py-20">
        <div class="w-12 h-12 bg-brand-50 rounded-2xl flex items-center justify-center mx-auto mb-3">
          <SIcon name="alert-circle" :size="24" :stroke-width="1.5" class="text-brand-500" />
        </div>
        <p class="text-fg-secondary font-medium">尚未設定任何告警規則</p>
      </div>

      <table v-else class="w-full text-sm bg-surface-raised border border-neutral-200 rounded-xl overflow-hidden">
        <thead>
          <tr class="bg-surface-sunken text-xs uppercase tracking-wider text-fg-tertiary text-left">
            <th class="px-4 py-3 font-semibold">範圍</th>
            <th class="px-4 py-3 font-semibold">閾值</th>
            <th class="px-4 py-3 font-semibold">管道</th>
            <th class="px-4 py-3 font-semibold">目標</th>
            <th class="px-4 py-3 font-semibold text-center">啟用</th>
            <th class="px-4 py-3 font-semibold text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in items" :key="a.id"
              class="border-t border-neutral-100 hover:bg-neutral-50/40 transition">
            <td class="px-4 py-3">
              <span class="inline-flex items-center px-2 py-0.5 rounded-md text-xs"
                    :class="a.scope === 'workspace' ? 'bg-brand-50 text-brand-700' : 'bg-neutral-100 text-fg-secondary'">
                {{ a.scope === 'workspace' ? 'Workspace' : 'User' }}
              </span>
            </td>
            <td class="px-4 py-3 font-mono text-fg">{{ a.threshold_pct }}%</td>
            <td class="px-4 py-3 text-fg-secondary">{{ a.channel }}</td>
            <td class="px-4 py-3 max-w-[300px] truncate text-fg-secondary" :title="a.target">{{ a.target }}</td>
            <td class="px-4 py-3 text-center">
              <input
                type="checkbox"
                :checked="a.enabled"
                @change="toggle(a)"
                class="h-4 w-4 cursor-pointer"
              />
            </td>
            <td class="px-4 py-3 text-right">
              <button
                @click="remove(a)"
                class="px-2 py-1 text-xs text-danger-700 hover:bg-danger-50 rounded-md transition"
                title="刪除"
              >
                <SIcon name="trash" :size="14" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create modal -->
    <div v-if="showCreate" class="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40"
         @click.self="closeCreate">
      <div class="bg-surface-raised rounded-xl border border-neutral-200 shadow-xl w-full max-w-md p-5">
        <h3 class="text-base font-semibold text-fg">新增告警規則</h3>

        <div class="mt-4 space-y-3">
          <div>
            <label class="block text-xs text-fg-secondary mb-1">範圍</label>
            <select v-model="form.scope"
              class="w-full h-9 px-3 text-sm rounded-md border border-neutral-200 bg-surface-raised text-fg">
              <option value="workspace">Workspace</option>
              <option value="user">User</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-fg-secondary mb-1">閾值（%）</label>
            <div class="flex gap-2">
              <button
                v-for="p in [80, 90, 100]"
                :key="p"
                type="button"
                @click="form.threshold_pct = p"
                class="px-3 py-1.5 text-xs rounded-md border transition"
                :class="form.threshold_pct === p
                  ? 'bg-brand-600 text-white border-brand-600'
                  : 'bg-surface-raised text-fg-secondary border-neutral-200 hover:bg-neutral-50'"
              >{{ p }}%</button>
              <input v-model.number="form.threshold_pct" type="number" min="1" max="200"
                class="w-20 h-8 px-2 text-sm rounded-md border border-neutral-200 bg-surface-raised text-fg" />
            </div>
          </div>
          <div>
            <label class="block text-xs text-fg-secondary mb-1">管道</label>
            <select v-model="form.channel"
              class="w-full h-9 px-3 text-sm rounded-md border border-neutral-200 bg-surface-raised text-fg">
              <option value="email">Email</option>
              <option value="slack">Slack webhook</option>
              <option value="webhook">Webhook</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-fg-secondary mb-1">目標</label>
            <input v-model="form.target" type="text"
              :placeholder="form.channel === 'email' ? 'admin@example.com' : 'https://...'"
              class="w-full h-9 px-3 text-sm rounded-md border border-neutral-200 bg-surface-raised text-fg" />
          </div>
          <div class="flex items-center gap-2">
            <input id="alert-enabled" v-model="form.enabled" type="checkbox" class="h-4 w-4" />
            <label for="alert-enabled" class="text-xs text-fg-secondary">啟用</label>
          </div>
        </div>

        <div class="mt-5 flex justify-end gap-2">
          <button
            @click="closeCreate"
            class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50"
          >取消</button>
          <button
            @click="create"
            :disabled="saving || !form.target"
            class="px-3 py-1.5 text-xs text-white bg-brand-600 hover:bg-brand-700 rounded-lg disabled:opacity-50"
          >{{ saving ? '建立中…' : '建立' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { SIcon, SSpinner } from '@staffkm/ui-kit'
import {
  quotaAlertApi,
  type QuotaAlert,
  type QuotaAlertCreate,
} from '../../api/quotaAlert'

const items   = ref<QuotaAlert[]>([])
const loading = ref(true)
const saving  = ref(false)
const showCreate = ref(false)

const form = reactive<QuotaAlertCreate>({
  scope:         'workspace',
  threshold_pct: 80,
  channel:       'email',
  target:        '',
  enabled:       true,
})

async function load() {
  loading.value = true
  try {
    items.value = await quotaAlertApi.list()
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '載入失敗')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.scope = 'workspace'
  form.threshold_pct = 80
  form.channel = 'email'
  form.target = ''
  form.enabled = true
  showCreate.value = true
}

function closeCreate() {
  showCreate.value = false
}

async function create() {
  saving.value = true
  try {
    await quotaAlertApi.create({ ...form })
    closeCreate()
    await load()
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '建立失敗')
  } finally {
    saving.value = false
  }
}

async function toggle(a: QuotaAlert) {
  try {
    await quotaAlertApi.update(a.id, { enabled: !a.enabled })
    await load()
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '更新失敗')
  }
}

async function remove(a: QuotaAlert) {
  if (!confirm(`確定刪除這個 ${a.scope} ${a.threshold_pct}% ${a.channel} 告警規則？`)) return
  try {
    await quotaAlertApi.delete(a.id)
    await load()
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '刪除失敗')
  }
}

onMounted(load)
</script>
