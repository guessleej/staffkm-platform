<template>
  <div class="flex flex-col h-full">
    <!-- 頁首 -->
    <div class="bg-surface-raised border-b border-neutral-200 px-6 py-4 flex items-center justify-between flex-shrink-0">
      <div>
        <h1 class="text-lg font-semibold text-fg">人工核可</h1>
        <p class="text-sm text-fg-tertiary mt-0.5">Workflow human_approval 節點觸發的待審事項</p>
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
          <SIcon name="check-circle" :size="24" :stroke-width="1.5" class="text-brand-500" />
        </div>
        <p class="text-fg-secondary font-medium">沒有符合條件的核可項目</p>
      </div>

      <table v-else class="w-full text-sm bg-surface-raised border border-neutral-200 rounded-xl overflow-hidden">
        <thead>
          <tr class="bg-surface-sunken text-xs uppercase tracking-wider text-fg-tertiary text-left">
            <th class="px-4 py-3 font-semibold">建立時間</th>
            <th class="px-4 py-3 font-semibold">Run</th>
            <th class="px-4 py-3 font-semibold">Node</th>
            <th class="px-4 py-3 font-semibold">內容預覽</th>
            <th class="px-4 py-3 font-semibold text-center">狀態</th>
            <th class="px-4 py-3 font-semibold text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in items" :key="a.id"
              class="border-t border-neutral-100 hover:bg-neutral-50/40 transition align-top">
            <td class="px-4 py-3 text-fg-secondary whitespace-nowrap">{{ fmt(a.created_at) }}</td>
            <td class="px-4 py-3 font-mono text-xs text-fg-secondary" :title="a.run_id">
              {{ a.run_id.slice(0, 8) }}…
            </td>
            <td class="px-4 py-3 text-fg">{{ a.node_key }}</td>
            <td class="px-4 py-3 max-w-[420px]">
              <div class="text-fg-secondary text-xs whitespace-pre-wrap break-words line-clamp-3">
                {{ preview(a.payload) || '—' }}
              </div>
            </td>
            <td class="px-4 py-3 text-center">
              <span class="inline-flex items-center px-2 py-0.5 rounded-md text-xs"
                    :class="statusClass(a.status)">
                {{ statusLabel(a.status) }}
              </span>
              <div v-if="a.status !== 'pending' && a.approver_note" class="mt-1 text-[10px] text-fg-tertiary">
                備註：{{ a.approver_note }}
              </div>
            </td>
            <td class="px-4 py-3 text-right whitespace-nowrap">
              <template v-if="a.status === 'pending'">
                <button
                  @click="openResolve(a, 'approved')"
                  class="px-2.5 py-1 text-xs text-success-700 hover:bg-success-50 rounded-md transition mr-1"
                  title="核准"
                >
                  <SIcon name="check" :size="14" />
                </button>
                <button
                  @click="openResolve(a, 'rejected')"
                  class="px-2.5 py-1 text-xs text-danger-700 hover:bg-danger-50 rounded-md transition"
                  title="拒絕"
                >
                  <SIcon name="x" :size="14" />
                </button>
              </template>
              <span v-else class="text-xs text-fg-tertiary">{{ fmt(a.resolved_at) }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- resolve modal -->
    <div v-if="resolving" class="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40"
         @click.self="closeResolve">
      <div class="bg-surface-raised rounded-xl border border-neutral-200 shadow-xl w-full max-w-md p-5">
        <h3 class="text-base font-semibold text-fg">
          {{ resolving.action === 'approved' ? '核准' : '拒絕' }}此核可項目
        </h3>
        <p class="mt-2 text-xs text-fg-tertiary">
          Run <span class="font-mono">{{ resolving.approval.run_id.slice(0, 8) }}…</span> /
          Node {{ resolving.approval.node_key }}
        </p>

        <div class="mt-4">
          <label class="block text-xs text-fg-secondary mb-1">備註（選填）</label>
          <textarea v-model="resolving.note" rows="3"
            class="w-full px-3 py-2 text-sm rounded-md border border-neutral-200 bg-surface-raised text-fg"
            placeholder="留下決策原因，讓後續 audit 看到…"></textarea>
        </div>

        <div class="mt-5 flex justify-end gap-2">
          <button
            @click="closeResolve"
            class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50"
          >取消</button>
          <button
            @click="submitResolve"
            :disabled="saving"
            class="px-3 py-1.5 text-xs text-white rounded-lg disabled:opacity-50"
            :class="resolving.action === 'approved'
              ? 'bg-success-600 hover:bg-success-700'
              : 'bg-danger-600 hover:bg-danger-700'"
          >{{ saving ? '送出中…' : (resolving.action === 'approved' ? '核准' : '拒絕') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { SIcon, SSpinner } from '@staffkm/ui-kit'
import {
  approvalApi,
  type WorkflowApproval,
  type ApprovalStatus,
} from '../../api/approval'

const FILTER_OPTS: { value: ApprovalStatus | undefined; label: string }[] = [
  { value: undefined,  label: '全部' },
  { value: 'pending',  label: '待審' },
  { value: 'approved', label: '已核准' },
  { value: 'rejected', label: '已拒絕' },
]

const items   = ref<WorkflowApproval[]>([])
const loading = ref(true)
const saving  = ref(false)
const filter  = ref<ApprovalStatus | undefined>('pending')

const resolving = ref<{
  approval: WorkflowApproval
  action: 'approved' | 'rejected'
  note: string
} | null>(null)

async function load() {
  loading.value = true
  try {
    const res = await approvalApi.list(filter.value)
    items.value = res.items || []
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '載入失敗')
  } finally {
    loading.value = false
  }
}

function setFilter(v: ApprovalStatus | undefined) {
  filter.value = v
  load()
}

function openResolve(approval: WorkflowApproval, action: 'approved' | 'rejected') {
  resolving.value = { approval, action, note: '' }
}

function closeResolve() {
  resolving.value = null
}

async function submitResolve() {
  if (!resolving.value) return
  saving.value = true
  try {
    const { approval, action, note } = resolving.value
    if (action === 'approved') await approvalApi.approve(approval.id, note || undefined)
    else                       await approvalApi.reject(approval.id,  note || undefined)
    closeResolve()
    await load()
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '送出失敗')
  } finally {
    saving.value = false
  }
}

function statusClass(s: ApprovalStatus): string {
  if (s === 'pending')  return 'bg-warning-50 text-warning-700'
  if (s === 'approved') return 'bg-success-50 text-success-700'
  return 'bg-danger-50 text-danger-700'
}

function statusLabel(s: ApprovalStatus): string {
  return s === 'pending' ? '待審'
       : s === 'approved' ? '已核准'
       : '已拒絕'
}

function preview(payload: any): string {
  if (!payload) return ''
  if (typeof payload === 'string') return payload
  return payload.context_preview || JSON.stringify(payload).slice(0, 200)
}

function fmt(ts: string | null): string {
  if (!ts) return '—'
  try { return new Date(ts).toLocaleString('zh-TW', { hour12: false }) }
  catch { return ts }
}

onMounted(load)
</script>
