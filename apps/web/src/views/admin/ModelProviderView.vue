<template>
  <div class="flex-1 flex flex-col overflow-hidden">
    <!-- 頁首 -->
    <div class="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between flex-shrink-0">
      <div>
        <h1 class="text-lg font-semibold text-gray-900">模型供應商管理</h1>
        <p class="text-sm text-gray-500 mt-0.5">管理 LLM、Embedding、Reranker 等 AI 模型供應商</p>
      </div>
      <button @click="openProviderDialog()" class="btn-primary flex items-center gap-2">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
        </svg>
        新增供應商
      </button>
    </div>

    <!-- 內容 -->
    <div class="flex-1 overflow-y-auto p-6">
      <!-- 供應商列表 -->
      <div v-if="loading" class="flex justify-center py-20">
        <svg class="animate-spin w-8 h-8 text-indigo-500" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
        </svg>
      </div>

      <div v-else-if="providers.length === 0" class="text-center py-20">
        <div class="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <svg class="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23-.693L5 14.5m14.8.8l1.402 1.402c1 1 .03 2.798-1.442 2.798H4.24c-1.47 0-2.44-1.798-1.442-2.798L4.2 15.3"/>
          </svg>
        </div>
        <p class="text-gray-500 text-sm">尚未新增任何模型供應商</p>
        <button @click="openProviderDialog()" class="mt-4 btn-primary">新增供應商</button>
      </div>

      <div v-else class="space-y-4">
        <div
          v-for="provider in providers"
          :key="provider.id"
          class="bg-white rounded-xl border border-gray-200 overflow-hidden"
        >
          <!-- 供應商標頭 -->
          <div class="flex items-center justify-between px-5 py-4 border-b border-gray-100">
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 rounded-lg flex items-center justify-center text-lg"
                   :class="providerIconBg(provider.provider_type)">
                {{ providerIcon(provider.provider_type) }}
              </div>
              <div>
                <div class="flex items-center gap-2">
                  <span class="font-semibold text-gray-900 text-sm">{{ provider.name }}</span>
                  <span class="badge" :class="provider.status === 'active' ? 'badge-green' : 'badge-gray'">
                    {{ provider.status === 'active' ? '啟用' : '停用' }}
                  </span>
                </div>
                <p class="text-xs text-gray-400 mt-0.5">{{ provider.base_url || '預設端點' }}</p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <button @click="verifyProvider(provider)" class="btn-sm btn-outline" :disabled="verifying === provider.id">
                <span v-if="verifying === provider.id">驗證中…</span>
                <span v-else>測試連線</span>
              </button>
              <button @click="openModelDialog(provider)"
                      class="btn-sm btn-outline inline-flex items-center gap-1 whitespace-nowrap">
                <svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
                </svg>
                <span>新增模型</span>
              </button>
              <button @click="openProviderDialog(provider)" class="btn-sm btn-ghost">編輯</button>
              <button @click="deleteProvider(provider.id)" class="btn-sm text-rose-500 hover:bg-rose-50">刪除</button>
            </div>
          </div>

          <!-- 模型列表 -->
          <div class="px-5 py-3">
            <div v-if="!modelsByProvider[provider.id]?.length" class="text-xs text-gray-400 py-1">
              尚未定義任何模型 — 點擊「新增模型」開始
            </div>
            <div v-else class="flex flex-wrap gap-2">
              <div
                v-for="model in modelsByProvider[provider.id]"
                :key="model.id"
                class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs"
                :class="model.is_default ? 'border-indigo-300 bg-indigo-50 text-indigo-700' : 'border-gray-200 bg-gray-50 text-gray-600'"
              >
                <span class="font-mono">{{ model.model_name }}</span>
                <span class="badge text-[10px]" :class="modelTypeBadge(model.model_type)">{{ model.model_type }}</span>
                <span v-if="model.is_default" class="text-indigo-400">★</span>
                <button @click="deleteModel(model.id, provider.id)" class="ml-1 text-gray-300 hover:text-rose-400">×</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 供應商 Dialog -->
    <div v-if="showProviderDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4">
        <div class="px-6 pt-6 pb-4 border-b border-gray-100">
          <h3 class="text-base font-semibold text-gray-900">
            {{ editingProvider ? '編輯供應商' : '新增模型供應商' }}
          </h3>
        </div>
        <div class="p-6 space-y-4">
          <div>
            <label class="form-label">供應商名稱</label>
            <input v-model="providerForm.name" class="form-input" placeholder="如：OpenAI 正式環境"
                   autocomplete="off" data-1p-ignore data-lpignore="true" />
          </div>
          <div>
            <label class="form-label">類型</label>
            <select v-model="providerForm.provider_type" class="form-input" @change="onProviderTypeChange">
              <option v-for="r in registry" :key="r.type" :value="r.type">{{ r.label }}</option>
              <option value="custom">自訂</option>
            </select>
            <p v-if="selectedRegistry?.notes" class="mt-1 text-[11px] text-gray-500">
              {{ selectedRegistry.notes }}
            </p>
          </div>
          <div>
            <label class="form-label">
              Base URL（選填）
              <span v-if="selectedRegistry?.default_base_url" class="ml-1 text-[11px] text-gray-400">
                預設：{{ selectedRegistry.default_base_url }}
              </span>
            </label>
            <input v-model="providerForm.base_url" class="form-input font-mono text-sm"
                   :placeholder="selectedRegistry?.default_base_url || 'https://api.openai.com/v1'"
                   autocomplete="off" data-1p-ignore data-lpignore="true"
                   inputmode="url" spellcheck="false" />
          </div>
          <div v-if="selectedRegistry?.needs_api_key !== false">
            <label class="form-label">API Key</label>
            <input v-model="providerForm.api_key" type="password" class="form-input font-mono text-sm"
                   :placeholder="editingProvider ? '留空保持不變' : 'sk-...'"
                   autocomplete="new-password" data-1p-ignore data-lpignore="true" />
          </div>
          <div v-else class="text-[11px] text-gray-500 bg-gray-50 rounded-md px-3 py-2">
            此供應商為地端服務，無需 API Key
          </div>
        </div>
        <div class="px-6 pb-6 flex justify-end gap-3">
          <button @click="showProviderDialog = false" class="btn-outline">取消</button>
          <button @click="saveProvider" class="btn-primary" :disabled="saving">
            {{ saving ? '儲存中…' : '儲存' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 模型 Dialog -->
    <div v-if="showModelDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4">
        <div class="px-6 pt-6 pb-4 border-b border-gray-100">
          <h3 class="text-base font-semibold text-gray-900">新增模型 — {{ currentProvider?.name }}</h3>
        </div>
        <div class="p-6 space-y-4">
          <div>
            <label class="form-label">模型 ID</label>
            <input v-model="modelForm.model_name" class="form-input font-mono text-sm" list="recommended-models"
                   placeholder="gpt-4o / llama3 / text-embedding-3-small"/>
            <datalist id="recommended-models">
              <option v-for="m in recommendedModelsForCurrent" :key="m" :value="m" />
            </datalist>
            <p v-if="recommendedModelsForCurrent.length" class="mt-1 text-[11px] text-gray-500">
              建議：{{ recommendedModelsForCurrent.join(' · ') }}
            </p>
          </div>
          <div>
            <label class="form-label">顯示名稱（選填）</label>
            <input v-model="modelForm.display_name" class="form-input" placeholder="GPT-4o"/>
          </div>
          <div>
            <label class="form-label">模型類型</label>
            <select v-model="modelForm.model_type" class="form-input">
              <option value="llm">LLM（對話）</option>
              <option value="embedding">Embedding（向量化）</option>
              <option value="reranker">Reranker（重排序）</option>
              <option value="tts">TTS（語音合成）</option>
              <option value="stt">STT（語音識別）</option>
            </select>
          </div>
          <div class="flex items-center gap-2">
            <input id="is_default" v-model="modelForm.is_default" type="checkbox" class="w-4 h-4 accent-indigo-600"/>
            <label for="is_default" class="text-sm text-gray-700">設為此類型的預設模型</label>
          </div>
        </div>
        <div class="px-6 pb-6 flex justify-end gap-3">
          <button @click="showModelDialog = false" class="btn-outline">取消</button>
          <button @click="saveModel" class="btn-primary" :disabled="saving">
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

const loading = ref(false)
const saving = ref(false)
const verifying = ref<string | null>(null)
const providers = ref<ModelProvider[]>([])
const modelsByProvider = ref<Record<string, AiModel[]>>({})

const showProviderDialog = ref(false)
const showModelDialog = ref(false)
const editingProvider = ref<ModelProvider | null>(null)
const currentProvider = ref<ModelProvider | null>(null)

const providerForm = reactive({ name: '', provider_type: 'openai', base_url: '', api_key: '' })
const modelForm = reactive({ model_name: '', model_type: 'llm', display_name: '', is_default: false })

// M3 中段-C：Provider Registry
const registry = ref<ProviderRegistryEntry[]>([])
const selectedRegistry = computed<ProviderRegistryEntry | undefined>(() =>
  registry.value.find(r => r.type === providerForm.provider_type),
)
const recommendedModelsForCurrent = computed<string[]>(() => {
  const meta = registry.value.find(r => r.type === currentProvider.value?.provider_type)
  return meta?.recommended_models ?? []
})
async function loadRegistry() {
  try { registry.value = await providerRegistryApi.list() }
  catch (e) { console.warn('provider registry load failed:', e) }
}
function onProviderTypeChange() {
  const meta = selectedRegistry.value
  if (meta?.default_base_url && !providerForm.base_url) {
    providerForm.base_url = meta.default_base_url
  }
}

async function loadProviders() {
  loading.value = true
  try {
    const { data } = await modelProviderApi.listProviders()
    providers.value = data.data?.items ?? data.data ?? []
    await Promise.all(providers.value.map(p => loadModels(p.id)))
  } finally {
    loading.value = false
  }
}

async function loadModels(providerId: string) {
  const { data } = await modelProviderApi.listModels(providerId)
  modelsByProvider.value[providerId] = data.data ?? []
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

async function saveProvider() {
  saving.value = true
  try {
    const payload: any = { ...providerForm }
    if (!payload.api_key) delete payload.api_key
    if (editingProvider.value) {
      await modelProviderApi.updateProvider(editingProvider.value.id, payload)
    } else {
      await modelProviderApi.createProvider(payload)
    }
    showProviderDialog.value = false
    await loadProviders()
  } finally {
    saving.value = false
  }
}

async function deleteProvider(id: string) {
  if (!confirm('確定要刪除此供應商？相關模型定義也會一併刪除。')) return
  await modelProviderApi.deleteProvider(id)
  await loadProviders()
}

async function verifyProvider(p: ModelProvider) {
  verifying.value = p.id
  try {
    const { data } = await modelProviderApi.verifyProvider(p.id)
    alert(data.data?.message ?? '連線成功')
  } catch (e: any) {
    alert('連線失敗：' + (e.response?.data?.detail ?? e.message))
  } finally {
    verifying.value = null
  }
}

function openModelDialog(p: ModelProvider) {
  currentProvider.value = p
  Object.assign(modelForm, { model_name: '', model_type: 'llm', display_name: '', is_default: false })
  showModelDialog.value = true
}

async function saveModel() {
  if (!currentProvider.value) return
  saving.value = true
  try {
    await modelProviderApi.createModel(currentProvider.value.id, { ...modelForm })
    showModelDialog.value = false
    await loadModels(currentProvider.value.id)
  } finally {
    saving.value = false
  }
}

async function deleteModel(modelId: string, providerId: string) {
  if (!confirm('確定刪除此模型定義？')) return
  await modelProviderApi.deleteModel(modelId)
  await loadModels(providerId)
}

function providerIcon(type: string) {
  const m: Record<string, string> = { openai: 'OAI', ollama: 'OLL', azure: 'AZ', anthropic: 'ANT', custom: 'CST' }
  return m[type] ?? 'LLM'
}
function providerIconBg(type: string) {
  const m: Record<string, string> = { openai: 'bg-emerald-50', ollama: 'bg-orange-50', azure: 'bg-sky-50', anthropic: 'bg-violet-50', custom: 'bg-gray-100' }
  return m[type] ?? 'bg-gray-100'
}
function modelTypeBadge(type: string) {
  const m: Record<string, string> = { llm: 'badge-indigo', embedding: 'badge-sky', reranker: 'badge-orange', tts: 'badge-purple', stt: 'badge-green' }
  return m[type] ?? 'badge-gray'
}

onMounted(async () => { await Promise.all([loadProviders(), loadRegistry()]) })
</script>

<style scoped>
.btn-primary { @apply px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition disabled:opacity-50; }
.btn-outline { @apply px-3 py-1.5 border border-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition disabled:opacity-50; }
.btn-ghost { @apply px-3 py-1.5 text-gray-600 text-sm font-medium rounded-lg hover:bg-gray-100 transition; }
.btn-sm { @apply px-2.5 py-1 text-xs font-medium rounded-lg transition; }
.form-label { @apply block text-xs font-semibold text-gray-600 mb-1; }
.form-input { @apply w-full h-9 px-3 text-sm rounded-lg border border-gray-200 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 outline-none transition bg-white; }
.badge { @apply px-1.5 py-0.5 rounded text-[10px] font-semibold; }
.badge-green { @apply bg-emerald-100 text-emerald-700; }
.badge-gray { @apply bg-gray-100 text-gray-500; }
.badge-indigo { @apply bg-indigo-100 text-indigo-700; }
.badge-sky { @apply bg-sky-100 text-sky-700; }
.badge-orange { @apply bg-orange-100 text-orange-700; }
.badge-purple { @apply bg-purple-100 text-purple-700; }
</style>
