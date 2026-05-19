<template>
  <div class="flex-1 flex flex-col overflow-hidden bg-surface-base">
    <!-- 頁首 -->
    <div class="bg-surface-raised border-b border-bd px-6 py-4 flex-shrink-0">
      <h1 class="text-lg font-semibold text-fg">模型管理</h1>
      <p class="text-sm text-fg-tertiary mt-0.5">設定預設模型 / 新增供應商 / 管理 API Key</p>
    </div>

    <div class="flex-1 overflow-hidden flex">
      <!-- 主區（左 + 中）-->
      <div class="flex-1 overflow-y-auto p-6 space-y-6">
        <!-- 1. 設定預設模型 -->
        <section class="bg-surface-raised border border-bd rounded-2xl p-6">
          <h2 class="text-base font-semibold text-fg mb-1">設定預設模型</h2>
          <p class="text-xs text-fg-tertiary mb-4">每個 workspace 預設使用的模型；個別 application 可覆寫</p>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div v-for="kind in MODEL_KINDS" :key="kind.key">
              <label class="block text-sm text-fg-secondary mb-1.5">
                <span :class="kind.required ? 'text-danger-600 mr-0.5' : ''">{{ kind.required ? '*' : '' }}</span>
                {{ kind.label }}
                <span class="text-xs text-fg-tertiary ml-1">({{ kind.modelType }})</span>
              </label>
              <select
                v-model="defaults[kind.key]"
                @change="saveDefault(kind.key)"
                class="w-full px-3 py-2 text-sm rounded-md border border-bd bg-surface-raised text-fg
                       focus:outline-none focus:ring-1 focus:ring-brand-400"
              >
                <option value="">未選擇</option>
                <option
                  v-for="m in modelsOfType(kind.modelType)"
                  :key="m.id"
                  :value="m.model_name"
                >{{ m.display_name || m.model_name }} ({{ providerName(m.provider_id) }})</option>
              </select>
            </div>
          </div>
        </section>

        <!-- 2. 已加供應商 -->
        <section>
          <div class="flex items-center justify-between mb-3">
            <h2 class="text-base font-semibold text-fg">已加供應商</h2>
            <button @click="openProviderDialog()" class="text-xs text-brand-600 hover:underline flex items-center gap-1">
              <SIcon name="plus" :size="12" /> 自訂供應商
            </button>
          </div>

          <div v-if="loading" class="flex justify-center py-12"><SSpinner :size="24" /></div>

          <div v-else-if="providers.length === 0"
               class="text-center py-12 bg-surface-raised border border-bd rounded-2xl">
            <SIcon name="database" :size="28" :stroke-width="1.5" class="text-fg-tertiary mx-auto mb-2" />
            <p class="text-sm text-fg-tertiary">尚未新增任何供應商 — 從右側點「+ 添加模型」開始</p>
          </div>

          <div v-else class="space-y-2">
            <div
              v-for="p in providers" :key="p.id"
              class="bg-surface-raised border border-bd rounded-xl"
            >
              <!-- header row -->
              <div class="flex items-center justify-between p-3">
                <div class="flex items-center gap-3 min-w-0">
                  <div class="w-9 h-9 rounded-lg flex items-center justify-center text-xs font-semibold flex-shrink-0"
                       :style="{background: providerColor(p.provider_type), color: '#fff'}">
                    {{ providerInitials(p.name) }}
                  </div>
                  <div class="min-w-0">
                    <div class="text-sm font-medium text-fg flex items-center gap-2">
                      {{ p.name }}
                      <span class="text-[10px] px-1.5 py-0.5 rounded uppercase font-semibold bg-success-100 text-success-700"
                            v-if="p.status === 'active'">啟用</span>
                    </div>
                    <div class="text-xs text-fg-tertiary truncate">{{ p.base_url || '—' }}</div>
                  </div>
                </div>
                <div class="flex items-center gap-2 flex-shrink-0">
                  <button @click="verifyProvider(p)" class="text-xs px-2.5 py-1.5 rounded-md border border-bd hover:bg-neutral-50 text-fg-secondary flex items-center gap-1">
                    <SIcon name="check-circle" :size="12" /> 測試
                  </button>
                  <button @click="openModelDialog(p)" class="text-xs px-2.5 py-1.5 rounded-md border border-bd hover:bg-neutral-50 text-fg-secondary flex items-center gap-1">
                    <SIcon name="plus" :size="12" /> 新增模型
                  </button>
                  <button @click="openProviderDialog(p)" class="text-xs text-fg-secondary hover:text-fg px-2 py-1">編輯</button>
                  <button @click="deleteProvider(p.id)" class="text-xs text-danger-600 hover:text-danger-700 px-2 py-1">刪除</button>
                </div>
              </div>
              <!-- models -->
              <div v-if="(modelsByProvider[p.id] || []).length > 0"
                   class="border-t border-neutral-100 px-3 py-2 flex flex-wrap gap-1.5">
                <span
                  v-for="m in (modelsByProvider[p.id] || [])" :key="m.id"
                  class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] bg-neutral-50 border border-neutral-200 text-fg-secondary"
                >
                  <span class="font-medium">{{ m.display_name || m.model_name }}</span>
                  <span class="text-fg-tertiary">·</span>
                  <span class="text-fg-tertiary">{{ m.model_type }}</span>
                  <button @click="deleteModel(m.id, p.id)" class="text-fg-tertiary hover:text-danger-600 ml-0.5">×</button>
                </span>
              </div>
            </div>
          </div>
        </section>
      </div>

      <!-- 右側 catalog -->
      <aside class="w-[340px] flex-shrink-0 border-l border-bd bg-surface-raised flex flex-col">
        <div class="p-4 border-b border-bd flex-shrink-0">
          <h2 class="text-sm font-semibold text-fg mb-2">可用供應商</h2>
          <div class="relative">
            <SIcon name="search" :size="14" class="absolute left-2.5 top-1/2 -translate-y-1/2 text-fg-tertiary" />
            <input
              v-model="catalogSearch"
              placeholder="搜尋供應商…"
              class="w-full h-8 pl-8 pr-2 text-sm rounded-md border border-bd bg-surface-base text-fg
                     focus:outline-none focus:ring-1 focus:ring-brand-400"
            />
          </div>
          <div class="flex flex-wrap gap-1 mt-2">
            <button
              v-for="t in CATALOG_TABS" :key="t"
              @click="catalogTab = t"
              :class="['text-[11px] px-2 py-0.5 rounded font-medium transition-colors',
                       catalogTab === t
                         ? 'bg-brand-600 text-white'
                         : 'bg-neutral-100 text-fg-secondary hover:bg-neutral-200']"
            >{{ t }}</button>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto p-3 space-y-2">
          <div v-if="catalogLoading" class="flex justify-center py-12"><SSpinner :size="20" /></div>
          <div v-else-if="filteredCatalog.length === 0" class="text-xs text-fg-tertiary text-center py-8">沒有符合的供應商</div>

          <div
            v-for="entry in filteredCatalog" :key="entry.type"
            class="border border-bd rounded-lg p-3 hover:border-brand-300 hover:bg-brand-50/30 transition-colors"
          >
            <div class="flex items-start justify-between mb-1.5">
              <div class="flex items-center gap-2 min-w-0">
                <div class="w-7 h-7 rounded flex items-center justify-center text-[10px] font-bold text-white flex-shrink-0"
                     :style="{background: providerColor(entry.type)}">
                  {{ providerInitials(entry.label) }}
                </div>
                <div class="min-w-0">
                  <div class="text-sm font-medium text-fg truncate flex items-center gap-1">
                    {{ entry.label }}
                    <span v-if="entry.is_local" class="text-[9px] px-1 py-0 rounded bg-success-100 text-success-700 font-semibold uppercase">地端</span>
                  </div>
                </div>
              </div>
              <button
                @click="addFromCatalog(entry)"
                class="text-[11px] px-2 py-0.5 rounded-md bg-brand-600 text-white hover:bg-brand-700 flex items-center gap-0.5 flex-shrink-0"
              >
                <SIcon name="plus" :size="10" />添加
              </button>
            </div>
            <p v-if="entry.notes" class="text-[11px] text-fg-tertiary leading-snug mb-1.5 line-clamp-2" :title="entry.notes">{{ entry.notes }}</p>
            <div class="flex flex-wrap gap-1">
              <span
                v-for="cap in (entry.capabilities || [])" :key="cap"
                class="text-[10px] px-1.5 py-0.5 rounded bg-neutral-100 text-fg-tertiary uppercase font-medium"
              >{{ cap }}</span>
            </div>
          </div>
        </div>
      </aside>
    </div>

    <!-- Provider dialog (新增 / 編輯) -->
    <div v-if="showProviderDialog" class="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" @click.self="showProviderDialog = false">
      <div class="bg-surface-raised rounded-2xl shadow-2xl w-full max-w-md">
        <div class="px-6 py-4 border-b border-bd">
          <h3 class="text-base font-semibold text-fg">{{ editingProvider ? '編輯供應商' : '新增供應商' }}</h3>
        </div>
        <div class="px-6 py-4 space-y-4">
          <div>
            <label class="block text-sm text-fg-secondary mb-1">名稱</label>
            <input v-model="providerForm.name" placeholder="如：OpenAI 正式環境" class="w-full px-3 py-2 text-sm rounded-md border border-bd bg-surface-raised" />
          </div>
          <div>
            <label class="block text-sm text-fg-secondary mb-1">類型</label>
            <select v-model="providerForm.provider_type" @change="onProviderTypeChange" class="w-full px-3 py-2 text-sm rounded-md border border-bd bg-surface-raised">
              <option v-for="r in registry" :key="r.type" :value="r.type">{{ r.label }}</option>
              <option value="custom">自訂</option>
            </select>
          </div>
          <div>
            <label class="block text-sm text-fg-secondary mb-1">Base URL（選填）</label>
            <input v-model="providerForm.base_url" placeholder="https://api.openai.com/v1" class="w-full px-3 py-2 text-sm rounded-md border border-bd bg-surface-raised" />
          </div>
          <div>
            <label class="block text-sm text-fg-secondary mb-1">API Key</label>
            <input v-model="providerForm.api_key" type="password" placeholder="sk-..." class="w-full px-3 py-2 text-sm rounded-md border border-bd bg-surface-raised" />
            <p v-if="editingProvider" class="text-xs text-fg-tertiary mt-1">留空 = 不變更現有 API Key</p>
          </div>
        </div>
        <div class="px-6 pb-6 flex justify-end gap-2">
          <button @click="showProviderDialog = false" class="px-4 py-2 text-sm text-fg-secondary">取消</button>
          <button @click="saveProvider" :disabled="saving" class="px-4 py-2 text-sm bg-brand-600 text-white rounded-md hover:bg-brand-700 disabled:opacity-50">
            {{ saving ? '儲存中…' : '儲存' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Model dialog -->
    <div v-if="showModelDialog" class="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" @click.self="showModelDialog = false">
      <div class="bg-surface-raised rounded-2xl shadow-2xl w-full max-w-md">
        <div class="px-6 py-4 border-b border-bd">
          <h3 class="text-base font-semibold text-fg">新增模型 — {{ currentProvider?.name }}</h3>
        </div>
        <div class="px-6 py-4 space-y-4">
          <div>
            <label class="block text-sm text-fg-secondary mb-1">Model Name</label>
            <input v-model="modelForm.model_name" :placeholder="recommendedModelsForCurrent[0] || 'gpt-4o-mini'" class="w-full px-3 py-2 text-sm rounded-md border border-bd bg-surface-raised" />
            <div v-if="recommendedModelsForCurrent.length" class="flex flex-wrap gap-1 mt-1.5">
              <button
                v-for="rec in recommendedModelsForCurrent" :key="rec"
                @click="modelForm.model_name = rec"
                class="text-[11px] px-1.5 py-0.5 rounded bg-neutral-100 hover:bg-brand-50 text-fg-secondary border border-neutral-200"
              >{{ rec }}</button>
            </div>
          </div>
          <div>
            <label class="block text-sm text-fg-secondary mb-1">類型</label>
            <select v-model="modelForm.model_type" class="w-full px-3 py-2 text-sm rounded-md border border-bd bg-surface-raised">
              <option value="llm">LLM</option>
              <option value="embedding">Embedding</option>
              <option value="reranker">Reranker</option>
              <option value="image">Image (DALL-E etc)</option>
              <option value="stt">STT (Whisper)</option>
              <option value="tts">TTS</option>
              <option value="vision">Vision (img2txt)</option>
            </select>
          </div>
          <div>
            <label class="block text-sm text-fg-secondary mb-1">顯示名稱（選填）</label>
            <input v-model="modelForm.display_name" class="w-full px-3 py-2 text-sm rounded-md border border-bd bg-surface-raised" />
          </div>
        </div>
        <div class="px-6 pb-6 flex justify-end gap-2">
          <button @click="showModelDialog = false" class="px-4 py-2 text-sm text-fg-secondary">取消</button>
          <button @click="saveModel" :disabled="saving" class="px-4 py-2 text-sm bg-brand-600 text-white rounded-md hover:bg-brand-700 disabled:opacity-50">
            {{ saving ? '儲存中…' : '新增' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { modelProviderApi, providerRegistryApi, type ModelProvider, type AiModel, type ProviderRegistryEntry } from '../../api/modelProvider'
import { systemSettingsApi } from '../../api/systemSettings'
import { SIcon, SSpinner } from '@staffkm/ui-kit'

// ── 預設模型欄位定義 ──────────────────────────────────────────────
const MODEL_KINDS = [
  { key: 'default.llm',       label: '聊天模型',     modelType: 'llm',       required: true  },
  { key: 'default.embedding', label: '嵌入模型',     modelType: 'embedding', required: false },
  { key: 'default.vision',    label: 'img2Txt 模型', modelType: 'vision',    required: false },
  { key: 'default.stt',       label: 'speech2Txt 模型', modelType: 'stt',    required: false },
  { key: 'default.rerank',    label: 'rerank 模型',  modelType: 'reranker',  required: false },
  { key: 'default.tts',       label: '語音合成模型', modelType: 'tts',       required: false },
] as const

const CATALOG_TABS = ['All', '地端', 'LLM', 'Embedding', 'Reranker', 'TTS', 'STT', 'Vision', 'Image'] as const

// ── State ───────────────────────────────────────────────────────
const loading = ref(false)
const catalogLoading = ref(false)
const saving = ref(false)
const providers = ref<ModelProvider[]>([])
const modelsByProvider = ref<Record<string, AiModel[]>>({})
const registry = ref<ProviderRegistryEntry[]>([])
const defaults = ref<Record<string, string>>({})

const catalogSearch = ref('')
const catalogTab = ref<typeof CATALOG_TABS[number]>('All')

const showProviderDialog = ref(false)
const showModelDialog = ref(false)
const editingProvider = ref<ModelProvider | null>(null)
const currentProvider = ref<ModelProvider | null>(null)

const providerForm = reactive({ name: '', provider_type: 'openai', base_url: '', api_key: '' })
const modelForm = reactive({ model_name: '', model_type: 'llm', display_name: '', is_default: false })

const selectedRegistry = computed<ProviderRegistryEntry | undefined>(() =>
  registry.value.find(r => r.type === providerForm.provider_type),
)
const recommendedModelsForCurrent = computed<string[]>(() => {
  const meta = registry.value.find(r => r.type === currentProvider.value?.provider_type)
  return meta?.recommended_models ?? []
})

// ── 全 model flat list（給 dropdown 用）────────────────────────
const allModels = computed<AiModel[]>(() => {
  const out: AiModel[] = []
  Object.values(modelsByProvider.value).forEach(arr => arr.forEach(m => out.push(m)))
  return out
})
function modelsOfType(t: string): AiModel[] {
  return allModels.value.filter(m => m.model_type === t)
}
function providerName(providerId: string): string {
  return providers.value.find(p => p.id === providerId)?.name || ''
}

// ── Catalog filter ──────────────────────────────────────────────
const filteredCatalog = computed(() => {
  return registry.value.filter(r => {
    if (catalogSearch.value &&
        !r.label.toLowerCase().includes(catalogSearch.value.toLowerCase()) &&
        !r.type.toLowerCase().includes(catalogSearch.value.toLowerCase())) return false
    if (catalogTab.value === '地端') {
      if (!r.is_local) return false
    } else if (catalogTab.value !== 'All') {
      const caps = (r.capabilities || []).map(c => c.toLowerCase())
      if (!caps.includes(catalogTab.value.toLowerCase())) return false
    }
    return true
  })
})

// ── Provider visual helpers ─────────────────────────────────────
const COLORS: Record<string, string> = {
  // 國際雲
  openai: '#10a37f', anthropic: '#cc785c', azure_openai: '#0078d4',
  bedrock: '#ff9900', gemini: '#4285f4', vertex_ai: '#4285f4',
  cohere: '#39594d', mistral: '#f97316', groq: '#f55036',
  together: '#1c64f2', fireworks: '#ff6b35', perplexity: '#20808d',
  openrouter: '#6366f1', xai: '#000000', nvidia_nim: '#76b900',
  // 地端 serving
  ollama: '#000000', llama_cpp: '#a16207', vllm: '#2563eb',
  sglang: '#7c3aed', tgi: '#f59e0b', lmstudio: '#9333ea',
  xinference: '#10b981', localai: '#0891b2', text_gen_webui: '#475569',
  gpt4all: '#dc2626',
  // 中文雲
  deepseek: '#4d6bfe', zhipu: '#3b82f6', moonshot: '#000000',
  qwen: '#615ced', baichuan: '#dc2626', minimax: '#7c3aed',
  siliconflow: '#06b6d4', yi: '#00a86b', doubao: '#ef4444',
  hunyuan: '#0052d9', qianfan: '#2932e1', bailian: '#ff6a00',
  // Specialty
  voyage: '#9333ea', jina: '#fbbf24', elevenlabs: '#000000',
  deepgram: '#13ef93', stability_ai: '#7c3aed',
}
function providerColor(type: string): string {
  return COLORS[type] || '#6366f1'
}
function providerInitials(name: string): string {
  const cleaned = name.replace(/[^a-zA-Z0-9一-龥]/g, '')
  return cleaned.slice(0, 3).toUpperCase()
}

// ── Load ────────────────────────────────────────────────────────
async function loadRegistry() {
  catalogLoading.value = true
  try { registry.value = await providerRegistryApi.list() }
  catch (e) { console.warn('registry load failed', e) }
  finally { catalogLoading.value = false }
}

async function loadProviders() {
  loading.value = true
  try {
    const { data } = await modelProviderApi.listProviders()
    providers.value = data.data?.items ?? data.data ?? []
    await Promise.all(providers.value.map(p => loadModels(p.id)))
  } finally { loading.value = false }
}

async function loadModels(providerId: string) {
  const { data } = await modelProviderApi.listModels(providerId)
  modelsByProvider.value[providerId] = data.data ?? []
}

async function loadDefaults() {
  try {
    const data = await systemSettingsApi.list()
    for (const item of data.items) {
      if (item.key.startsWith('default.')) {
        defaults.value[item.key] = item.value || ''
      }
    }
  } catch (e) { console.warn('defaults load failed', e) }
}

async function saveDefault(key: string) {
  try {
    await systemSettingsApi.update(key, defaults.value[key])
  } catch (e) {
    console.error('save default failed', e)
    alert('儲存失敗，請重試')
  }
}

// ── Provider CRUD ───────────────────────────────────────────────
function onProviderTypeChange() {
  const meta = selectedRegistry.value
  if (meta?.default_base_url && !providerForm.base_url) {
    providerForm.base_url = meta.default_base_url
  }
}

function openProviderDialog(p?: ModelProvider) {
  editingProvider.value = p ?? null
  Object.assign(providerForm, {
    name: p?.name ?? '',
    provider_type: p?.provider_type ?? 'openai',
    base_url: p?.base_url ?? '',
    api_key: '',
  })
  showProviderDialog.value = true
}

function addFromCatalog(entry: ProviderRegistryEntry) {
  editingProvider.value = null
  Object.assign(providerForm, {
    name: entry.label,
    provider_type: entry.type,
    base_url: entry.default_base_url || '',
    api_key: '',
  })
  showProviderDialog.value = true
}

async function saveProvider() {
  saving.value = true
  try {
    const payload: any = {
      name: providerForm.name,
      provider_type: providerForm.provider_type,
      base_url: providerForm.base_url || null,
    }
    if (providerForm.api_key) payload.api_key = providerForm.api_key
    if (editingProvider.value) {
      await modelProviderApi.updateProvider(editingProvider.value.id, payload)
    } else {
      await modelProviderApi.createProvider(payload)
    }
    showProviderDialog.value = false
    await loadProviders()
  } catch (e: any) {
    alert(e?.response?.data?.detail || '儲存失敗')
  } finally { saving.value = false }
}

async function deleteProvider(id: string) {
  if (!confirm('確定刪除此供應商？所有模型也會被一併刪除。')) return
  await modelProviderApi.deleteProvider(id)
  await loadProviders()
}

async function verifyProvider(p: ModelProvider) {
  try {
    const { data } = await modelProviderApi.verifyProvider(p.id)
    alert(data.data?.ok ? '✓ 連線成功' : `✗ ${data.data?.error || '驗證失敗'}`)
  } catch (e: any) {
    alert('驗證失敗：' + (e?.response?.data?.detail || ''))
  }
}

// ── Model CRUD ──────────────────────────────────────────────────
function openModelDialog(p: ModelProvider) {
  currentProvider.value = p
  Object.assign(modelForm, { model_name: '', model_type: 'llm', display_name: '', is_default: false })
  showModelDialog.value = true
}

async function saveModel() {
  if (!currentProvider.value) return
  saving.value = true
  try {
    await modelProviderApi.createModel(currentProvider.value.id, modelForm)
    showModelDialog.value = false
    await loadModels(currentProvider.value.id)
  } catch (e: any) {
    alert(e?.response?.data?.detail || '儲存失敗')
  } finally { saving.value = false }
}

async function deleteModel(modelId: string, providerId: string) {
  if (!confirm('確定刪除此模型？')) return
  await modelProviderApi.deleteModel(modelId)
  await loadModels(providerId)
}

onMounted(async () => {
  await Promise.all([loadRegistry(), loadProviders(), loadDefaults()])
})
</script>
