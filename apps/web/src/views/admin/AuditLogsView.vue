<template>
  <div class="flex flex-col h-full">
    <!-- 頁首 -->
    <div class="px-6 py-5 flex-shrink-0"><div class="card-hero flex items-center justify-between gap-4">
      <div>
        <h1 class="heading-page heading-accent">Audit Log</h1>
        <p class="text-sm text-fg-tertiary mt-0.5">操作紀錄 — 誰、何時、做了什麼</p>
      </div>
      <button @click="load" class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50 transition flex items-center gap-1">
        <SIcon name="refresh" :size="12" /> 重新整理
      </button>
    </div>

    <!-- Filter bar -->
    <div class="px-6 py-3 border-b border-neutral-100 flex items-center gap-2 flex-wrap flex-shrink-0">
      <label class="text-[11px] text-fg-tertiary">Action</label>
      <select v-model="filterAction" @change="load"
              class="h-8 px-2 text-xs rounded-md border border-neutral-200 bg-surface-raised">
        <option value="">全部</option>
        <option value="create">create</option>
        <option value="update">update</option>
        <option value="delete">delete</option>
        <option value="login">login</option>
        <option value="logout">logout</option>
        <option value="install">install</option>
      </select>
      <label class="text-[11px] text-fg-tertiary ml-2">Entity</label>
      <select v-model="filterEntity" @change="load"
              class="h-8 px-2 text-xs rounded-md border border-neutral-200 bg-surface-raised">
        <option value="">全部</option>
        <option value="application">application</option>
        <option value="kb">kb</option>
        <option value="project">project</option>
        <option value="api_key">api_key</option>
        <option value="template">template</option>
        <option value="user">user</option>
      </select>
      <div class="flex-1" />
      <span class="text-[11px] text-fg-tertiary">{{ total }} 筆</span>
    </div>

    <!-- table -->
</div>
    <div class="flex-1 overflow-y-auto p-6">
      <div v-if="loading" class="flex justify-center py-20">
        <SSpinner :size="24" />
      </div>

      <div v-else-if="!items.length" class="text-center py-20">
        <div class="w-12 h-12 bg-brand-50 rounded-2xl flex items-center justify-center mx-auto mb-3">
          <SIcon name="file-text" :size="24" :stroke-width="1.5" class="text-brand-500" />
        </div>
        <p class="text-fg-secondary font-medium">沒有 audit log</p>
        <p class="text-fg-tertiary text-sm mt-1">沒有操作或 filter 太嚴</p>
      </div>

      <table v-else class="w-full text-sm bg-surface-raised border border-bd rounded-2xl overflow-hidden shadow-sm">
        <thead>
          <tr class="bg-surface-sunken text-xs uppercase tracking-wider text-fg-tertiary text-left">
            <th class="px-4 py-3 font-semibold">時間</th>
            <th class="px-4 py-3 font-semibold">使用者</th>
            <th class="px-4 py-3 font-semibold">Action</th>
            <th class="px-4 py-3 font-semibold">Entity</th>
            <th class="px-4 py-3 font-semibold">標的</th>
            <th class="px-4 py-3 font-semibold">IP</th>
            <th class="px-4 py-3 font-semibold">Detail</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in items" :key="row.id"
              class="border-t border-neutral-100 hover:bg-neutral-50/40 transition">
            <td class="px-4 py-3 text-xs text-fg-secondary font-mono whitespace-nowrap">{{ fmt(row.created_at) }}</td>
            <td class="px-4 py-3">
              <p class="font-medium text-fg text-xs">{{ row.actor_username || '(system)' }}</p>
            </td>
            <td class="px-4 py-3">
              <span class="px-1.5 py-0.5 text-[10px] font-semibold rounded uppercase"
                    :class="actionBadge(row.action)">{{ row.action }}</span>
            </td>
            <td class="px-4 py-3 text-xs text-fg-secondary font-mono">{{ row.entity_type }}</td>
            <td class="px-4 py-3 text-xs">
              <p class="text-fg truncate max-w-[200px]" :title="row.entity_label || row.entity_id || ''">
                {{ row.entity_label || row.entity_id || '—' }}
              </p>
            </td>
            <td class="px-4 py-3 text-[11px] text-fg-tertiary font-mono">{{ row.ip_address || '—' }}</td>
            <td class="px-4 py-3 text-[11px]">
              <details v-if="hasDetail(row)" class="cursor-pointer">
                <summary class="text-fg-tertiary hover:text-fg">看</summary>
                <pre class="mt-1 p-2 bg-neutral-50 rounded text-[10px] font-mono text-fg-secondary overflow-x-auto max-w-md">{{ JSON.stringify(row.detail, null, 2) }}</pre>
              </details>
              <span v-else class="text-fg-tertiary">—</span>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- pagination -->
      <div v-if="totalPages > 1" class="mt-4 flex items-center justify-center gap-2">
        <button @click="page = Math.max(1, page-1); load()" :disabled="page <= 1"
                class="px-3 py-1.5 text-xs rounded border border-neutral-200 disabled:opacity-50">← 上頁</button>
        <span class="text-xs text-fg-tertiary">{{ page }} / {{ totalPages }}</span>
        <button @click="page = Math.min(totalPages, page+1); load()" :disabled="page >= totalPages"
                class="px-3 py-1.5 text-xs rounded border border-neutral-200 disabled:opacity-50">下頁 →</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { SIcon, SSpinner } from '@staffkm/ui-kit'
import { auditApi, type AuditLog } from '../../api/audit'

const items = ref<AuditLog[]>([])
const loading = ref(true)
const total = ref(0)
const totalPages = ref(1)
const page = ref(1)
const filterAction = ref('')
const filterEntity = ref('')

async function load() {
  loading.value = true
  try {
    const r = await auditApi.list({
      action: filterAction.value || undefined,
      entity: filterEntity.value || undefined,
      page: page.value, page_size: 50,
    })
    items.value = r.items
    total.value = r.total
    totalPages.value = r.total_pages
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '載入失敗')
  } finally {
    loading.value = false
  }
}

function fmt(iso: string): string {
  const d = new Date(iso); if (isNaN(d.getTime())) return iso
  return d.toLocaleString('zh-TW', { hour12: false })
}
function actionBadge(action: string): string {
  if (['create','install','publish'].includes(action)) return 'bg-success-50 text-success-700'
  if (['delete','revoke'].includes(action))            return 'bg-danger-50 text-danger-700'
  if (['update','quota_change'].includes(action))      return 'bg-warning-50 text-warning-700'
  if (['login','logout'].includes(action))             return 'bg-info-50 text-info-700'
  return 'bg-neutral-100 text-fg-tertiary'
}
function hasDetail(row: AuditLog): boolean {
  return row.detail && Object.keys(row.detail).length > 0
}

onMounted(load)
</script>
