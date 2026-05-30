<template>
  <div class="flex flex-col h-full">
    <!-- 頁首 -->
    <div class="px-6 py-5 flex-shrink-0"><div class="card-hero flex items-center justify-between gap-4">
      <div>
        <h1 class="heading-page heading-accent">系統設定</h1>
        <p class="text-sm text-fg-tertiary mt-0.5">全域偏好、預設模型、上傳與安全策略</p>
      </div>
      <button
        @click="load"
        class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50 flex items-center gap-1"
      >
        <SIcon name="refresh" :size="12" /> 重新整理
      </button>
    </div>

    <!-- 提醒 -->
    <div class="bg-warning-50 border-b border-warning-200 px-6 py-3 flex-shrink-0 flex items-start gap-2">
      <SIcon name="alert-triangle" :size="14" class="text-warning-700 mt-0.5" />
      <div class="text-xs text-warning-700">
        <p class="font-medium">⚠ 此頁設定為「顯示 / advisory」，修改不會即時改變 runtime 行為</p>
        <p>Embedding / Reranker / RRF 權重 / 上傳 / 安全策略的實際運行值由 <code class="font-mono">.env</code> 或 per-call body 決定。請改用：<b>模型</b> → <a href="/admin/models" class="underline">模型管理</a>（即時生效）；<b>嵌入模型</b> → 知識庫「重新索引」流程；<b>其餘</b> → 部署 <code class="font-mono">.env.production</code> 後重啟服務。</p>
      </div>
    </div>

    <!-- 內容 -->
</div>
    <div class="flex-1 overflow-y-auto p-6 space-y-6">
      <div v-if="loading" class="flex justify-center py-20">
        <SSpinner :size="24" />
      </div>

      <template v-else>
        <section v-for="g in groups" :key="g.prefix">
          <h2 class="text-xs uppercase tracking-wider text-fg-tertiary font-semibold mb-3 flex items-center gap-2">
            {{ g.label }}
            <span class="normal-case tracking-normal text-[10px] text-warning-700 bg-warning-50 border border-warning-200 px-1.5 py-0.5 rounded">advisory</span>
          </h2>
          <div class="grid gap-3 md:grid-cols-2">
            <div
              v-for="s in g.items" :key="s.key"
              class="bg-surface-raised border border-neutral-200 rounded-xl p-4"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <p class="text-sm font-medium text-fg break-all">{{ s.key }}</p>
                  <p v-if="s.description" class="text-[11px] text-fg-tertiary mt-0.5">{{ s.description }}</p>
                </div>
                <span v-if="flash[s.key]" class="text-[10px] text-success-700 bg-success-50 px-2 py-0.5 rounded">已儲存</span>
              </div>

              <div class="mt-3">
                <!-- boolean -->
                <label v-if="kind(s.value) === 'boolean'" class="inline-flex items-center gap-2">
                  <input type="checkbox" v-model="drafts[s.key]" class="rounded border-neutral-300 text-brand-600 focus:ring-brand-500" />
                  <span class="text-sm text-fg-secondary">{{ drafts[s.key] ? '已啟用' : '已停用' }}</span>
                </label>

                <!-- number -->
                <input
                  v-else-if="kind(s.value) === 'number'"
                  v-model.number="drafts[s.key]" type="number"
                  class="w-full h-9 px-3 text-sm rounded-md border border-neutral-200 bg-surface-raised text-fg focus:outline-none focus:ring-1 focus:ring-brand-400"
                />

                <!-- array (string[]) -->
                <input
                  v-else-if="kind(s.value) === 'array'"
                  v-model="draftStrings[s.key]"
                  placeholder="以逗號分隔"
                  class="w-full h-9 px-3 text-sm font-mono rounded-md border border-neutral-200 bg-surface-raised text-fg focus:outline-none focus:ring-1 focus:ring-brand-400"
                />

                <!-- object (系統管理的 JSON 狀態，唯讀) -->
                <div v-else-if="kind(s.value) === 'object'">
                  <pre class="w-full px-3 py-2 text-xs font-mono rounded-md border border-neutral-200 bg-neutral-100 text-fg-secondary overflow-auto max-h-48 whitespace-pre">{{ prettyJson(s.value) }}</pre>
                  <p class="text-[10px] text-fg-tertiary mt-1">系統自動維護，唯讀</p>
                </div>

                <!-- string / fallback -->
                <input
                  v-else
                  v-model="drafts[s.key]" type="text"
                  class="w-full h-9 px-3 text-sm rounded-md border border-neutral-200 bg-surface-raised text-fg focus:outline-none focus:ring-1 focus:ring-brand-400"
                />
              </div>

              <div class="mt-3 flex items-center justify-between text-[11px] text-fg-tertiary">
                <span>最後更新：{{ fmtDate(s.updated_at) }}</span>
                <button
                  v-if="kind(s.value) !== 'object'"
                  @click="save(s)"
                  :disabled="busy[s.key] || !changed(s)"
                  class="px-3 py-1 text-[11px] text-white bg-brand-600 hover:bg-brand-700 rounded disabled:opacity-40"
                >
                  {{ busy[s.key] ? '儲存中…' : '儲存' }}
                </button>
              </div>
            </div>
          </div>
        </section>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, reactive, computed } from 'vue'
import { SIcon, SSpinner } from '@staffkm/ui-kit'
import { systemSettingsApi, type SystemSetting } from '../../api/systemSettings'

const settings = ref<SystemSetting[]>([])
const loading = ref(true)

const drafts = reactive<Record<string, any>>({})
const draftStrings = reactive<Record<string, string>>({})  // 給 array type 用
const busy = reactive<Record<string, boolean>>({})
const flash = reactive<Record<string, boolean>>({})

const GROUPS: { prefix: string; label: string }[] = [
  { prefix: 'embedding', label: 'Embedding' },
  { prefix: 'reranker',  label: 'Reranker' },
  { prefix: 'search',    label: 'Hybrid Search' },
  { prefix: 'upload',    label: 'Upload' },
  { prefix: 'security',  label: 'Security' },
]

const groups = computed(() => {
  return GROUPS.map(g => ({
    ...g,
    items: settings.value.filter(s => s.key.startsWith(g.prefix + '.')),
  })).filter(g => g.items.length > 0)
})

function kind(v: any): 'boolean' | 'number' | 'array' | 'object' | 'string' {
  if (typeof v === 'boolean') return 'boolean'
  if (typeof v === 'number')  return 'number'
  if (Array.isArray(v))       return 'array'
  if (v !== null && typeof v === 'object') return 'object'
  return 'string'
}

function prettyJson(v: any): string {
  try { return JSON.stringify(v, null, 2) } catch { return String(v) }
}

function resetDraft(s: SystemSetting) {
  if (kind(s.value) === 'array') {
    draftStrings[s.key] = (s.value as any[]).join(', ')
  } else {
    drafts[s.key] = s.value
  }
}

function changed(s: SystemSetting): boolean {
  if (kind(s.value) === 'array') {
    const parsed = parseArray(draftStrings[s.key] || '')
    return JSON.stringify(parsed) !== JSON.stringify(s.value)
  }
  return drafts[s.key] !== s.value
}

function parseArray(raw: string): string[] {
  return raw.split(',').map(x => x.trim()).filter(Boolean)
}

async function load() {
  loading.value = true
  try {
    const r = await systemSettingsApi.list()
    settings.value = r.items || []
    for (const s of settings.value) resetDraft(s)
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '載入失敗')
  } finally {
    loading.value = false
  }
}

async function save(s: SystemSetting) {
  const value = kind(s.value) === 'array'
    ? parseArray(draftStrings[s.key] || '')
    : drafts[s.key]
  busy[s.key] = true
  try {
    await systemSettingsApi.update(s.key, value)
    s.value = value
    s.updated_at = new Date().toISOString()
    flash[s.key] = true
    setTimeout(() => { flash[s.key] = false }, 1800)
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '儲存失敗')
  } finally {
    busy[s.key] = false
  }
}

function fmtDate(s?: string | null): string {
  if (!s) return '—'
  try { return new Date(s).toLocaleString('zh-TW', { hour12: false }) } catch { return s }
}

onMounted(load)
</script>
