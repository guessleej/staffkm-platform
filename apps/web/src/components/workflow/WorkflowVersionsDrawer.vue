<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-transform duration-300 ease-out"
      enter-from-class="translate-x-full"
      leave-active-class="transition-transform duration-200 ease-in"
      leave-to-class="translate-x-full"
    >
      <aside v-if="modelValue"
             class="fixed top-0 right-0 h-full w-[440px] z-50 bg-surface-raised border-l border-neutral-200 flex flex-col shadow-2xl">
        <header class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between flex-shrink-0">
          <div class="min-w-0">
            <p class="text-[10px] uppercase tracking-widest text-fg-tertiary">VERSIONS</p>
            <h3 class="font-semibold text-sm text-fg">Workflow 版本歷史</h3>
          </div>
          <button @click="close" class="p-1.5 rounded-md text-fg-tertiary hover:text-fg hover:bg-neutral-100">
            <SIcon name="x" :size="18" />
          </button>
        </header>

        <!-- 快照 form -->
        <div class="px-5 py-3 border-b border-neutral-100 bg-neutral-50/40 flex-shrink-0">
          <label class="block text-xs font-semibold text-fg-secondary mb-1.5">
            建立新版本（快照當前 workflow）
          </label>
          <div class="flex gap-2">
            <input v-model="newNote"
                   placeholder="這版改了什麼？選填"
                   class="flex-1 h-9 px-3 text-sm rounded-lg border border-neutral-200 focus:border-brand-500 focus:ring-2 focus:ring-brand-100 outline-none" />
            <button @click="onSnapshot"
                    :disabled="busy"
                    class="h-9 px-3 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 disabled:opacity-50 rounded-lg flex items-center gap-1">
              <SIcon name="check" :size="14" />
              快照
            </button>
          </div>
        </div>

        <!-- 列表 -->
        <div class="flex-1 overflow-y-auto px-5 py-4">
          <div v-if="loading" class="flex justify-center py-10">
            <SSpinner :size="24" />
          </div>
          <p v-else-if="!versions.length" class="text-sm text-fg-tertiary text-center py-10">
            尚無版本快照
          </p>
          <ul v-else class="space-y-3">
            <li v-for="(v, i) in versions" :key="v.id"
                class="border border-neutral-200 rounded-lg p-3 hover:border-brand-300 transition">
              <div class="flex items-start gap-3">
                <div class="w-9 h-9 rounded-lg bg-brand-50 flex items-center justify-center font-bold text-brand-700 flex-shrink-0">
                  v{{ v.version_number }}
                </div>
                <div class="min-w-0 flex-1">
                  <p class="text-sm text-fg break-words">{{ v.note || '（無備註）' }}</p>
                  <p class="text-[11px] text-fg-tertiary mt-1 font-mono">
                    {{ formatTime(v.created_at) }}
                  </p>
                </div>
                <span v-if="i === 0" class="px-1.5 py-0.5 text-[10px] font-semibold rounded bg-success-50 text-success-700 flex-shrink-0">
                  最新
                </span>
              </div>
              <button v-if="i !== 0"
                      @click="onRestore(v)"
                      :disabled="busy"
                      class="mt-2 ml-12 px-3 py-1 text-xs font-medium text-brand-700 bg-brand-50 hover:bg-brand-100 rounded transition disabled:opacity-50 flex items-center gap-1">
                <SIcon name="refresh" :size="12" />
                回滾到 v{{ v.version_number }}
              </button>
            </li>
          </ul>
        </div>

        <footer class="px-5 py-3 border-t border-neutral-100 text-[11px] text-fg-tertiary flex-shrink-0">
          💡 回滾會先把當前狀態快照成新版本，所以「上一版」隨時可救
        </footer>
      </aside>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { SIcon, SSpinner } from '@staffkm/ui-kit'
import { workflowApi, type WorkflowVersion } from '../../api/workflow'

const props = defineProps<{
  modelValue: boolean
  appId: string
}>()
const emit = defineEmits<{
  'update:modelValue': [v: boolean]
  'restored': []
}>()

const versions = ref<WorkflowVersion[]>([])
const loading = ref(false)
const busy = ref(false)
const newNote = ref('')

function close() { emit('update:modelValue', false) }

async function load() {
  loading.value = true
  try {
    versions.value = await workflowApi.listVersions(props.appId)
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '載入失敗')
  } finally {
    loading.value = false
  }
}

async function onSnapshot() {
  if (busy.value) return
  busy.value = true
  try {
    await workflowApi.createVersion(props.appId, newNote.value.trim() || undefined)
    newNote.value = ''
    await load()
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '快照失敗')
  } finally {
    busy.value = false
  }
}

async function onRestore(v: WorkflowVersion) {
  if (!confirm(`確定要回滾到 v${v.version_number}？目前狀態會先被自動快照成新版本（不會遺失）。`)) return
  busy.value = true
  try {
    await workflowApi.restoreVersion(props.appId, v.version_number)
    await load()
    emit('restored')  // 通知 parent 重 load canvas
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '回滾失敗')
  } finally {
    busy.value = false
  }
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  return d.toLocaleString('zh-TW', { hour12: false })
}

watch(() => props.modelValue, (open) => {
  if (open && props.appId) load()
})
</script>
