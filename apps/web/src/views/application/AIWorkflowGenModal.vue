<template>
  <div v-if="modelValue"
       class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
       @click.self="close">
    <div class="bg-surface-raised border border-bd rounded-xl shadow-xl w-[680px] max-h-[88vh] flex flex-col">
      <!-- header -->
      <div class="px-5 py-3 border-b border-bd flex items-center justify-between flex-shrink-0">
        <div class="flex items-center gap-2">
          <span class="text-sm font-semibold text-fg">AI 生成 workflow</span>
          <span class="text-[11px] text-fg-tertiary">v4.9 I</span>
        </div>
        <button @click="close"
                class="text-fg-tertiary hover:text-fg text-lg leading-none">×</button>
      </div>

      <!-- body -->
      <div class="p-5 overflow-y-auto space-y-4 flex-1">
        <div>
          <label class="block text-xs text-fg-secondary mb-1.5">
            描述你想要的 workflow（自然語言）
          </label>
          <textarea
            v-model="userRequest"
            rows="4"
            placeholder="例：我要做一個請假審批 workflow，超過 3 天要主管核准，核准後寄 email 通知"
            class="w-full px-3 py-2 text-sm border border-bd rounded-lg bg-surface-raised text-fg focus:border-indigo-400 focus:outline-none resize-none"
          />
        </div>

        <div class="flex items-center gap-2">
          <button
            @click="run"
            :disabled="loading || userRequest.trim().length < 5"
            class="px-4 py-1.5 bg-indigo-600 text-white text-xs font-semibold rounded-lg hover:bg-indigo-700 transition disabled:opacity-50"
          >
            {{ loading ? '生成中…' : '✨ AI 生成' }}
          </button>
          <span v-if="loading" class="text-xs text-fg-tertiary">呼叫 LLM 中，約 5-15 秒</span>
        </div>

        <!-- 結果 -->
        <div v-if="result" class="border border-bd rounded-lg p-3 bg-neutral-50 dark:bg-neutral-900 space-y-2">
          <div class="flex items-center gap-3 text-xs">
            <span :class="result.valid ? 'text-green-600' : 'text-red-600'" class="font-semibold">
              {{ result.valid ? '✓ 驗證通過' : '✗ 驗證失敗' }}
            </span>
            <span class="text-fg-tertiary">
              nodes: {{ result.workflow?.nodes?.length ?? 0 }} ／
              edges: {{ result.workflow?.edges?.length ?? 0 }}
            </span>
          </div>

          <div v-if="result.errors?.length" class="text-xs text-red-600 space-y-0.5">
            <div v-for="(e, i) in result.errors" :key="i">• {{ e }}</div>
          </div>

          <div v-if="result.workflow" class="flex items-center gap-2 pt-1">
            <button
              @click="applyToCanvas"
              :disabled="!result.valid"
              class="px-3 py-1 text-xs bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-40"
            >
              套用到畫布
            </button>
            <button
              @click="downloadJson"
              class="px-3 py-1 text-xs bg-surface-raised border border-bd rounded hover:border-indigo-400 text-fg-secondary"
            >
              下載 JSON
            </button>
            <button
              @click="copyJson"
              class="px-3 py-1 text-xs bg-surface-raised border border-bd rounded hover:border-indigo-400 text-fg-secondary"
            >
              複製
            </button>
            <label class="ml-auto text-[11px] text-fg-tertiary flex items-center gap-1 cursor-pointer">
              <input type="checkbox" v-model="showRaw" class="align-middle" />
              顯示 raw response (debug)
            </label>
          </div>

          <pre v-if="result.workflow"
               class="text-[11px] bg-surface-raised border border-bd rounded p-2 max-h-56 overflow-auto font-mono text-fg">{{ JSON.stringify(result.workflow, null, 2) }}</pre>

          <pre v-if="showRaw"
               class="text-[11px] bg-surface-raised border border-bd rounded p-2 max-h-40 overflow-auto font-mono text-fg-secondary whitespace-pre-wrap">{{ result.raw_response }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { workflowGenApi, type GenerateResult } from '../../api/workflowGen'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'apply', workflow: { nodes: any[]; edges: any[] }): void
}>()

const userRequest = ref('')
const loading     = ref(false)
const result      = ref<GenerateResult | null>(null)
const showRaw     = ref(false)

function close() {
  emit('update:modelValue', false)
}

async function run() {
  loading.value = true
  result.value = null
  try {
    result.value = await workflowGenApi.generate(userRequest.value.trim())
  } catch (e: any) {
    result.value = {
      workflow: null,
      valid: false,
      errors: [`API 失敗: ${e?.message || e}`],
      raw_response: '',
    }
  } finally {
    loading.value = false
  }
}

function applyToCanvas() {
  if (!result.value?.workflow) return
  const wf = result.value.workflow
  emit('apply', { nodes: wf.nodes || [], edges: wf.edges || [] })
  close()
}

function downloadJson() {
  if (!result.value?.workflow) return
  const blob = new Blob([JSON.stringify(result.value.workflow, null, 2)],
                       { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${result.value.workflow.name || 'workflow'}.json`
  a.click()
  URL.revokeObjectURL(url)
}

async function copyJson() {
  if (!result.value?.workflow) return
  try {
    await navigator.clipboard.writeText(JSON.stringify(result.value.workflow, null, 2))
  } catch {
    /* clipboard 失敗忽略 */
  }
}
</script>
