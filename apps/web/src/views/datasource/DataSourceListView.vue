<template>
  <div class="flex flex-col h-full">
    <div class="px-6 py-5 flex-shrink-0">
      <div class="card-hero flex items-center justify-between gap-4">
        <div>
          <h1 class="heading-page heading-accent">資料來源</h1>
          <p class="text-xs text-fg-tertiary mt-1">共 {{ items.length }} 個</p>
        </div>
        <button
          @click="showCreate = true"
          class="btn btn-primary"
        >
          <IconPlus :size="14" :stroke-width="2.5" />
          建立資料來源
        </button>
      </div>
    </div>

    <div class="flex-1 overflow-auto px-6 pb-6">
      <!-- 教學：如何建立一個資料來源（可收合）-->
      <div class="mb-4 bg-surface-raised border border-bd rounded-xl overflow-hidden">
        <button
          @click="showHelp = !showHelp"
          class="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-neutral-50 transition"
        >
          <span class="text-sm font-semibold text-fg flex items-center gap-2"><SIcon name="database" :size="16" class="text-brand-600" /> 如何建立一個資料來源？</span>
          <span class="text-xs text-fg-tertiary">{{ showHelp ? '收合 ▲' : '展開 ▼' }}</span>
        </button>
        <div v-if="showHelp" class="px-5 pb-5 text-sm text-fg-secondary space-y-3 border-t border-bd">
          <p class="pt-3">
            資料來源（Data Source）把<strong class="text-fg">外部資料庫 / API / 物件儲存</strong>接進來，
            讓 Application 能讀「知識庫文件以外」的即時資料（如訂單庫、報表 API）。
          </p>
          <div>
            <p class="font-medium text-fg mb-1">三步驟</p>
            <ol class="list-decimal list-inside space-y-1">
              <li>點右上 <strong class="text-fg">建立資料來源</strong>。</li>
              <li>選<strong class="text-fg">類型</strong>、填<strong class="text-fg">名稱</strong>與<strong class="text-fg">說明</strong>，按建立。</li>
              <li>建立後再設定<strong class="text-fg">連線參數</strong>（host / port / 帳密），然後在 Application 的資料節點選用。</li>
            </ol>
          </div>
          <div>
            <p class="font-medium text-fg mb-1">支援類型</p>
            <ul class="space-y-1">
              <li class="flex items-start gap-2"><SIcon name="database" :size="14" class="mt-0.5 shrink-0 text-brand-500" /><span><strong class="text-fg">資料庫</strong> — PostgreSQL / MySQL / SQL Server / MongoDB</span></li>
              <li class="flex items-start gap-2"><SIcon name="globe" :size="14" class="mt-0.5 shrink-0 text-brand-500" /><span><strong class="text-fg">API</strong> — REST API / GraphQL</span></li>
              <li class="flex items-start gap-2"><SIcon name="folder" :size="14" class="mt-0.5 shrink-0 text-brand-500" /><span><strong class="text-fg">物件儲存</strong> — S3</span></li>
            </ul>
          </div>
          <p class="text-xs text-fg-tertiary flex items-start gap-1.5">
            <SIcon name="lightbulb" :size="13" class="mt-0.5 shrink-0 text-amber-500" />
            <span>小提示：帳密等敏感連線參數在建立後另行設定、加密保存；建好可在 Application 流程裡當資料輸入。</span>
          </p>
        </div>
      </div>

      <p v-if="loading" class="text-sm text-fg-tertiary">載入中…</p>
      <EmptyState
        v-else-if="!items.length"
        icon="database"
        title="尚未建立資料來源"
        description="Data Source 可連結外部 DB / API 作為 Application 資料輸入"
        action-label="建立第一個資料來源"
        @action="showCreate = true"
      />
      <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <div
          v-for="(d, idx) in items" :key="d.id"
          class="card-warm fade-up p-5"
          :style="`animation-delay: ${idx * 40}ms`"
        >
          <div class="flex items-center justify-between mb-2">
            <h3 class="font-semibold text-sm text-neutral-900 truncate">{{ d.name }}</h3>
            <span class="text-[10px] uppercase tracking-widest text-neutral-400">{{ d.kind }}</span>
          </div>
          <p class="text-xs text-neutral-500 line-clamp-2 min-h-[2rem]">
            {{ d.description || '尚未填寫說明' }}
          </p>
          <div class="mt-3 flex items-center justify-between flex-wrap gap-2">
            <span
              class="text-[11px] px-2 py-0.5 rounded-full"
              :class="d.is_enabled ? 'bg-success-50 text-success-700' : 'bg-neutral-100 text-neutral-500'"
            >{{ d.is_enabled ? '啟用' : '停用' }}</span>
            <span v-if="d.last_synced_at" class="text-[10px] text-neutral-400">
              同步：{{ new Date(d.last_synced_at).toLocaleString('zh-TW') }}
            </span>
            <div class="flex items-center gap-2">
              <button
                @click="onTest(d.id)"
                :disabled="testingId === d.id"
                class="text-xs text-brand-600 hover:text-brand-800 transition disabled:opacity-40"
              >{{ testingId === d.id ? '測試中…' : '測試連線' }}</button>
              <button
                @click="onDelete(d.id)"
                class="text-xs text-neutral-400 hover:text-danger-600 transition"
              >刪除</button>
            </div>
          </div>
          <!-- 測試結果（D-3）-->
          <div
            v-if="testResults[d.id]"
            class="mt-2 px-3 py-2 text-xs rounded-md border"
            :class="testResults[d.id].success
              ? 'border-success-200 bg-success-50 text-success-800'
              : 'border-danger-200 bg-danger-50 text-danger-700'"
          >
            <p class="font-semibold">
              {{ testResults[d.id].success ? '成功' : '失敗' }}
              <span class="font-normal ml-2">{{ testResults[d.id].elapsed_ms }} ms</span>
            </p>
            <p class="mt-0.5 text-neutral-700">{{ testResults[d.id].detail }}</p>
          </div>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div
        v-if="showCreate"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30"
        @click.self="showCreate = false"
      >
        <div class="w-full max-w-md bg-surface-raised rounded-2xl shadow-2xl overflow-hidden">
          <div class="px-5 py-4 border-b border-neutral-100"><h3 class="text-sm font-semibold">建立資料來源</h3></div>
          <div class="px-5 py-4 space-y-3">
            <div>
              <label class="block text-xs text-neutral-500 mb-1">名稱</label>
              <input v-model="draft.name" class="form-input" @keydown.enter="(e) => { if (!(e as any).isComposing) { onCreate() } }" />
            </div>
            <div>
              <label class="block text-xs text-neutral-500 mb-1">類型</label>
              <select v-model="draft.kind" class="form-input">
                <option value="postgres">PostgreSQL</option>
                <option value="mysql">MySQL</option>
                <option value="mssql">SQL Server</option>
                <option value="mongo">MongoDB</option>
                <option value="rest">REST API</option>
                <option value="graphql">GraphQL</option>
                <option value="s3">S3 物件儲存</option>
              </select>
            </div>
            <div>
              <label class="block text-xs text-neutral-500 mb-1">說明</label>
              <textarea v-model="draft.description" rows="2" class="form-textarea" />
            </div>
            <p class="text-[11px] text-neutral-400">
              連線詳細參數（host / port / credentials）於建立後另行設定
            </p>
          </div>
          <div class="px-5 py-3 border-t border-neutral-100 bg-neutral-50 flex justify-end gap-2">
            <button @click="showCreate = false" class="h-9 px-4 text-sm rounded-lg border border-neutral-200">取消</button>
            <button :disabled="!draft.name.trim()" @click="onCreate" class="h-9 px-4 text-sm rounded-lg bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-40">建立</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { dataSourceApi, type DataSourceEntity, type DataSourceTestResult } from '../../api/extras'
import { SIcon } from '@staffkm/ui-kit'
import { IconPlus } from '../../components/icons'
import EmptyState from '../../components/common/EmptyState.vue'

const items = ref<DataSourceEntity[]>([])
const loading = ref(true)
const showCreate = ref(false)
const showHelp = ref(true)   // 教學卡：預設展開、可收合
const draft = reactive({ name: '', description: '', kind: 'postgres' })

async function load() {
  loading.value = true
  try { items.value = await dataSourceApi.list() } finally { loading.value = false }
}
async function onCreate() {
  if (!draft.name.trim()) return
  await dataSourceApi.create({ name: draft.name, description: draft.description || undefined, kind: draft.kind })
  draft.name = ''; draft.description = ''; draft.kind = 'postgres'
  showCreate.value = false
  await load()
}
async function onDelete(id: string) {
  if (!confirm('確定要刪除此資料來源？')) return
  await dataSourceApi.remove(id); await load()
}

// ── 連線測試 (D-3) ────────────────────────────────────────────────
const testingId = ref<string | null>(null)
const testResults = reactive<Record<string, DataSourceTestResult>>({})

async function onTest(id: string) {
  testingId.value = id
  try {
    testResults[id] = await dataSourceApi.test(id)
    // 測試成功時 backend 已更新 last_synced_at，refresh 列表反映
    if (testResults[id].success) await load()
  } catch (e: any) {
    testResults[id] = {
      success: false, elapsed_ms: 0,
      detail: e?.message || String(e),
      config_ok: false, missing: [],
    }
  } finally {
    testingId.value = null
  }
}

onMounted(load)
</script>
