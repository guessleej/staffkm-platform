<template>
  <div class="flex flex-col h-full overflow-hidden bg-surface-base">
    <!-- Header -->
    <div class="bg-surface-raised border-b border-neutral-200 px-6 py-3 flex items-center justify-between flex-shrink-0">
      <div class="flex items-center gap-3">
        <button
          @click="$router.push('/knowledge')"
          class="p-1.5 rounded-lg text-neutral-400 hover:text-fg hover:bg-neutral-100 transition-colors"
          title="返回"
        >
          <span class="text-base">←</span>
        </button>
        <div>
          <h1 class="heading-section text-fg">檢索測試</h1>
          <p class="text-[11px] text-fg-secondary font-mono">{{ kbId }}</p>
        </div>
      </div>
    </div>

    <!-- Body -->
    <div class="flex-1 overflow-auto px-6 py-4">
      <!-- Search bar + mode toggle -->
      <div class="max-w-4xl mx-auto space-y-3">
        <div class="flex gap-2">
          <input
            v-model="query"
            type="text"
            placeholder="輸入測試問題……"
            class="flex-1 h-10 px-3 text-sm bg-surface-raised border border-neutral-200 rounded-lg focus:border-brand-400 focus:outline-none text-fg placeholder:text-fg-secondary"
            @keydown.enter="runTest"
          />
          <button
            @click="runTest"
            :disabled="loading || !query.trim()"
            class="inline-flex items-center gap-1.5 h-10 px-4 text-sm font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-lg disabled:opacity-50 transition-colors"
          >
            {{ loading ? '檢索中…' : '檢索' }}
          </button>
        </div>

        <!-- search_mode segmented control -->
        <div class="flex items-center gap-3 flex-wrap text-xs">
          <span class="text-fg-secondary">檢索模式：</span>
          <div class="inline-flex rounded-lg border border-neutral-200 overflow-hidden">
            <button
              v-for="m in modes"
              :key="m.value"
              @click="searchMode = m.value"
              class="px-3 h-7 text-xs transition-colors"
              :class="searchMode === m.value
                ? 'bg-brand-600 text-white'
                : 'bg-surface-raised text-fg-secondary hover:bg-neutral-100'"
            >{{ m.label }}</button>
          </div>

          <span class="ml-3 text-fg-secondary">Top K：</span>
          <input
            v-model.number="topK"
            type="number" min="1" max="20"
            class="w-16 h-7 px-2 text-xs bg-surface-raised border border-neutral-200 rounded text-fg"
          />

          <label class="ml-3 inline-flex items-center gap-1.5 cursor-pointer">
            <input v-model="useReranker" type="checkbox" class="accent-brand-600" />
            <span class="text-fg-secondary">啟用 Reranker</span>
          </label>
        </div>

        <!-- Reranker config form -->
        <div v-if="useReranker"
             class="rounded-lg border border-warning-200 bg-warning-50 p-3 space-y-2 text-xs">
          <div class="font-semibold text-warning-700">Reranker 設定</div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <label class="flex flex-col gap-1">
              <span class="text-fg-secondary">類型</span>
              <select v-model="rerankerType"
                      class="h-8 px-2 bg-surface-raised border border-neutral-200 rounded text-fg">
                <option value="cohere">Cohere</option>
                <option value="http">HTTP (BGE Reranker)</option>
                <option value="ollama">Ollama</option>
              </select>
            </label>
            <label class="flex flex-col gap-1">
              <span class="text-fg-secondary">Model</span>
              <input v-model="rerankerModel" type="text" placeholder="bge-reranker-v2-m3"
                     class="h-8 px-2 bg-surface-raised border border-neutral-200 rounded text-fg" />
            </label>
            <label v-if="rerankerType !== 'cohere'" class="flex flex-col gap-1 sm:col-span-2">
              <span class="text-fg-secondary">Base URL</span>
              <input v-model="rerankerBaseUrl" type="text"
                     :placeholder="rerankerType === 'ollama' ? 'http://embedder:11434' : 'http://reranker:8080'"
                     class="h-8 px-2 bg-surface-raised border border-neutral-200 rounded text-fg" />
            </label>
            <label v-if="rerankerType !== 'ollama'" class="flex flex-col gap-1 sm:col-span-2">
              <span class="text-fg-secondary">API Key（選填）</span>
              <input v-model="rerankerApiKey" type="password"
                     class="h-8 px-2 bg-surface-raised border border-neutral-200 rounded text-fg" />
            </label>
            <label class="flex flex-col gap-1">
              <span class="text-fg-secondary">Rerank Top N</span>
              <input v-model.number="rerankTopN" type="number" min="1" max="20"
                     class="h-8 px-2 bg-surface-raised border border-neutral-200 rounded text-fg" />
            </label>
          </div>
        </div>

        <!-- Error -->
        <div v-if="error" class="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">
          {{ error }}
        </div>

        <!-- Results -->
        <div v-if="results.length" class="mt-2 space-y-2">
          <div class="text-xs text-fg-secondary">
            共命中 {{ results.length }} 筆
            <span v-if="reranked">（已 rerank）</span>
          </div>
          <div v-if="rerankWarning"
               class="text-xs px-2 py-1.5 rounded-md bg-warning-50 text-warning-700 border border-warning-200">
            ⚠ {{ rerankWarning }}
          </div>
          <div
            v-for="(r, idx) in results"
            :key="r.paragraph_id"
            class="rounded-lg border border-neutral-200 bg-surface-raised p-3 space-y-2"
          >
            <div class="flex items-center justify-between flex-wrap gap-2">
              <div class="flex items-center gap-2 text-xs">
                <span class="font-mono text-fg-secondary">#{{ idx + 1 }}</span>
                <span class="font-semibold text-fg">{{ r.doc_name }}</span>
                <span v-if="r.title" class="text-fg-secondary">— {{ r.title }}</span>
              </div>
              <div class="flex items-center gap-1.5 flex-wrap">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-brand-100 text-brand-700">
                  vector {{ fmt(r.vector_score) }}
                </span>
                <span v-if="r.rrf_score != null"
                      class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-violet-100 text-violet-700">
                  rrf {{ fmt(r.rrf_score) }}
                </span>
                <span v-if="r.rerank_score != null"
                      class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-warning-100 text-warning-700">
                  rerank {{ fmt(r.rerank_score) }}
                </span>
              </div>
            </div>
            <p class="text-xs text-fg whitespace-pre-wrap leading-relaxed">{{ r.content }}</p>
            <p class="font-mono text-[10px] text-fg-secondary">{{ r.paragraph_id }}</p>
          </div>
        </div>

        <div v-else-if="hasRun && !loading"
             class="text-center text-xs text-fg-secondary py-8">
          沒有命中任何段落
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { http } from '../../api'

const route = useRoute()
const kbId = computed(() => String(route.params.kbId))

const query = ref('')
const topK = ref(10)
const searchMode = ref<'hybrid' | 'vector' | 'fts'>('hybrid')
const modes = [
  { value: 'hybrid' as const, label: 'Hybrid' },
  { value: 'vector' as const, label: 'Vector' },
  { value: 'fts' as const, label: 'FTS' },
]

const useReranker = ref(false)
const rerankerType = ref<'cohere' | 'http' | 'ollama'>('http')
const rerankerModel = ref('bge-reranker-v2-m3')
const rerankerBaseUrl = ref('')
const rerankerApiKey = ref('')
const rerankTopN = ref(5)

const loading = ref(false)
const error = ref('')
const hasRun = ref(false)
const reranked = ref(false)
const rerankWarning = ref<string | null>(null)
const results = ref<any[]>([])

function fmt(n: number | null | undefined): string {
  if (n == null) return '—'
  return Number(n).toFixed(3)
}

async function runTest() {
  if (!query.value.trim()) return
  loading.value = true
  error.value = ''
  hasRun.value = true
  try {
    const body: any = {
      query: query.value,
      kb_id: kbId.value,
      top_k: topK.value,
      similarity_threshold: 0.3,
      vector_weight: 0.7,
      search_mode: searchMode.value,
    }
    if (useReranker.value) {
      const rcfg: any = { type: rerankerType.value }
      if (rerankerModel.value) rcfg.model_name = rerankerModel.value
      if (rerankerBaseUrl.value) rcfg.base_url = rerankerBaseUrl.value
      if (rerankerApiKey.value) rcfg.api_key = rerankerApiKey.value
      body.reranker = rcfg
      body.rerank_top_n = rerankTopN.value
    }
    const { data } = await http.post('/knowledge/hit-test', body)
    results.value = data.data?.results || []
    reranked.value = !!data.data?.reranked
    rerankWarning.value = data.data?.rerank_warning || null
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || '檢索失敗'
    results.value = []
    reranked.value = false
    rerankWarning.value = null
  } finally {
    loading.value = false
  }
}
</script>
