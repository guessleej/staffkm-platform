<template>
  <div class="flex flex-col h-full">
    <!-- 頁首 -->
    <div class="px-6 py-5 flex-shrink-0"><div class="card-hero flex items-center justify-between gap-4">
      <div>
        <h1 class="heading-page heading-accent">Multi-Region (v5.0)</h1>
        <p class="text-sm text-fg-tertiary mt-0.5">
          Active-active 區域註冊與衝突檢視 — 預設未啟用（scaffolding only）。
          詳見 <code class="text-xs">docs/deploy/active-active.md</code>。
        </p>
      </div>
      <button
        @click="loadAll"
        class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50 transition flex items-center gap-1"
      >
        <SIcon name="refresh" :size="12" /> 重新整理
      </button>
    </div>

</div>
    <div class="flex-1 overflow-y-auto p-6 space-y-8">
      <AdminHelp title="Multi-Region">
        <p>active-active <strong class='text-fg'>多區域</strong> scaffolding（預設關閉）；雙寫衝突解析與 region 路由的基礎設施。</p>
      </AdminHelp>
      <!-- ── Regions registry ─────────────────────────────────────── -->
      <section>
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-base font-semibold text-fg flex items-center gap-2">
            <SIcon name="globe" :size="16" /> 已註冊區域
          </h2>
        </div>

        <table class="w-full text-sm bg-surface-raised border border-bd rounded-2xl overflow-hidden shadow-sm">
          <thead>
            <tr class="bg-surface-sunken text-xs uppercase tracking-wider text-fg-tertiary text-left">
              <th class="px-4 py-3 font-semibold">ID</th>
              <th class="px-4 py-3 font-semibold">名稱</th>
              <th class="px-4 py-3 font-semibold">DB URL</th>
              <th class="px-4 py-3 font-semibold">MinIO Endpoint</th>
              <th class="px-4 py-3 font-semibold text-center">狀態</th>
              <th class="px-4 py-3 font-semibold text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!regions.length">
              <td colspan="6" class="px-4 py-8 text-center text-fg-tertiary">尚未註冊任何區域</td>
            </tr>
            <tr
              v-for="r in regions"
              :key="r.id"
              class="border-t border-neutral-100"
            >
              <td class="px-4 py-3 font-mono text-xs">{{ r.id }}</td>
              <td class="px-4 py-3">{{ r.name }}</td>
              <td class="px-4 py-3 text-xs text-fg-secondary truncate max-w-[200px]">{{ r.db_url || '—' }}</td>
              <td class="px-4 py-3 text-xs text-fg-secondary truncate max-w-[200px]">{{ r.minio_endpoint || '—' }}</td>
              <td class="px-4 py-3 text-center">
                <span
                  class="inline-block text-xs px-2 py-0.5 rounded"
                  :class="r.is_active ? 'bg-success-50 text-success-700' : 'bg-neutral-100 text-fg-tertiary'"
                >
                  {{ r.is_active ? 'active' : 'inactive' }}
                </span>
              </td>
              <td class="px-4 py-3 text-right">
                <button
                  v-if="r.is_active"
                  @click="deactivate(r.id)"
                  class="text-xs text-warning-600 hover:underline"
                >
                  停用
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- 新增 form -->
        <form
          @submit.prevent="createRegion"
          class="mt-3 flex flex-wrap gap-2 items-end p-3 bg-surface-raised border border-neutral-200 rounded-xl"
        >
          <div class="flex flex-col">
            <label class="text-xs text-fg-tertiary mb-1">Region ID</label>
            <input v-model="form.id" required placeholder="us-east-1"
                   class="px-2 py-1 text-sm border border-neutral-200 rounded" />
          </div>
          <div class="flex flex-col">
            <label class="text-xs text-fg-tertiary mb-1">名稱</label>
            <input v-model="form.name" required placeholder="US East"
                   class="px-2 py-1 text-sm border border-neutral-200 rounded" />
          </div>
          <div class="flex flex-col flex-1 min-w-[200px]">
            <label class="text-xs text-fg-tertiary mb-1">DB URL（選填）</label>
            <input v-model="form.db_url" placeholder="postgresql://..."
                   class="px-2 py-1 text-sm border border-neutral-200 rounded" />
          </div>
          <button type="submit"
                  class="px-3 py-1.5 text-xs bg-brand-500 text-white rounded hover:bg-brand-600">
            註冊
          </button>
        </form>
      </section>

      <!-- ── Conflicts ────────────────────────────────────────────── -->
      <section>
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-base font-semibold text-fg flex items-center gap-2">
            <SIcon name="alert-circle" :size="16" /> 衝突紀錄
          </h2>
          <div class="flex gap-1">
            <button
              v-for="opt in [{k: undefined, t: '全部'}, {k: 'pending', t: '待處理'}, {k: 'resolved', t: '已解決'}]"
              :key="String(opt.k)"
              @click="setStatus(opt.k as any)"
              class="px-2 py-1 text-xs rounded border"
              :class="conflictStatus === opt.k
                ? 'bg-brand-50 border-brand-300 text-brand-700'
                : 'bg-surface-raised border-neutral-200 text-fg-secondary'"
            >
              {{ opt.t }}
            </button>
          </div>
        </div>

        <table class="w-full text-sm bg-surface-raised border border-bd rounded-2xl overflow-hidden shadow-sm">
          <thead>
            <tr class="bg-surface-sunken text-xs uppercase tracking-wider text-fg-tertiary text-left">
              <th class="px-4 py-3 font-semibold">偵測時間</th>
              <th class="px-4 py-3 font-semibold">Entity</th>
              <th class="px-4 py-3 font-semibold">區域 A / B</th>
              <th class="px-4 py-3 font-semibold text-center">狀態</th>
              <th class="px-4 py-3 font-semibold text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!conflicts.length">
              <td colspan="5" class="px-4 py-8 text-center text-fg-tertiary">無衝突紀錄</td>
            </tr>
            <tr
              v-for="c in conflicts"
              :key="c.id"
              class="border-t border-neutral-100"
            >
              <td class="px-4 py-3 text-xs">{{ fmt(c.detected_at) }}</td>
              <td class="px-4 py-3 text-xs">
                <code>{{ c.entity_type }}</code>
                <span class="text-fg-tertiary">/{{ c.entity_id }}</span>
              </td>
              <td class="px-4 py-3 text-xs">{{ c.region_a }} ↔ {{ c.region_b }}</td>
              <td class="px-4 py-3 text-center">
                <span
                  class="inline-block text-xs px-2 py-0.5 rounded"
                  :class="c.resolution === 'pending'
                    ? 'bg-warning-50 text-warning-700'
                    : 'bg-success-50 text-success-700'"
                >
                  {{ c.resolution || 'pending' }}
                </span>
              </td>
              <td class="px-4 py-3 text-right">
                <button
                  v-if="c.resolution === 'pending'"
                  @click="resolveLww(c.id)"
                  class="text-xs text-brand-600 hover:underline"
                >
                  以 A 值解決 (LWW)
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { SIcon } from '@staffkm/ui-kit'
import { regionsApi, type Region, type ConflictRow } from '@/api/regions'

const regions = ref<Region[]>([])
const conflicts = ref<ConflictRow[]>([])
const conflictStatus = ref<'pending' | 'resolved' | undefined>(undefined)
const form = ref({ id: '', name: '', db_url: '', minio_endpoint: '' })

async function loadRegions() {
  try {
    regions.value = (await regionsApi.list()).items
  } catch {
    regions.value = []
  }
}

async function loadConflicts() {
  try {
    conflicts.value = (await regionsApi.listConflicts(conflictStatus.value)).items
  } catch {
    conflicts.value = []
  }
}

async function loadAll() {
  await Promise.all([loadRegions(), loadConflicts()])
}

function setStatus(s: 'pending' | 'resolved' | undefined) {
  conflictStatus.value = s
  loadConflicts()
}

async function createRegion() {
  await regionsApi.create({
    id: form.value.id,
    name: form.value.name,
    db_url: form.value.db_url || undefined,
    minio_endpoint: form.value.minio_endpoint || undefined,
  })
  form.value = { id: '', name: '', db_url: '', minio_endpoint: '' }
  await loadRegions()
}

async function deactivate(id: string) {
  if (!confirm(`停用區域 ${id}？`)) return
  await regionsApi.deactivate(id)
  await loadRegions()
}

async function resolveLww(id: string) {
  await regionsApi.resolveConflict(id, { resolution: 'lww' })
  await loadConflicts()
}

function fmt(s: string) {
  return new Date(s).toLocaleString()
}

onMounted(loadAll)
</script>
