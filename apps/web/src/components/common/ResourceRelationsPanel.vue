<template>
  <div class="flex flex-col h-full bg-surface-raised border border-bd rounded-lg overflow-hidden">
    <!-- Tabs -->
    <div class="flex border-b border-bd flex-shrink-0">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        @click="active = tab.key"
        class="flex-1 px-3 py-2 text-xs font-medium transition-colors"
        :class="active === tab.key
          ? 'text-fg border-b-2 border-brand-600 -mb-px'
          : 'text-fg-secondary hover:text-fg'"
      >
        {{ tab.label }}
        <span
          v-if="counts[tab.key] !== undefined"
          class="ml-1 text-[10px] px-1.5 py-0.5 rounded-full bg-neutral-100 text-neutral-700"
        >
          {{ counts[tab.key] }}
        </span>
      </button>
    </div>

    <!-- Body -->
    <div class="flex-1 overflow-y-auto">
      <div v-if="loading" class="flex items-center justify-center py-8 text-fg-secondary text-xs gap-2">
        <SIcon name="loader" :size="14" class="animate-spin" /> 載入中
      </div>
      <div v-else-if="error" class="px-3 py-4 text-xs text-danger-600">
        {{ error }}
      </div>
      <div v-else-if="!current.length" class="px-3 py-6 text-center text-xs text-fg-secondary">
        {{ active === 'depends' ? '沒有依賴的資源' : '尚未被其他資源使用' }}
      </div>
      <ul v-else class="divide-y divide-bd">
        <li
          v-for="item in current"
          :key="`${item.resource_type}:${item.id}`"
          class="px-3 py-2 hover:bg-neutral-50 cursor-pointer transition-colors"
          @click="goto(item)"
        >
          <div class="flex items-center gap-2">
            <SIcon :name="iconFor(item.resource_type)" :size="14" class="text-fg-secondary flex-shrink-0" />
            <div class="flex-1 min-w-0">
              <div class="text-xs font-medium text-fg truncate">{{ item.name || '(未命名)' }}</div>
              <div class="text-[10px] text-fg-secondary">{{ labelFor(item.resource_type) }}</div>
            </div>
            <SIcon name="external-link" :size="12" class="text-fg-secondary flex-shrink-0" />
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { SIcon } from '@staffkm/ui-kit'
import { http } from '../../api'

interface Relation {
  resource_type: string
  id: string
  name: string
  url: string
}

const props = defineProps<{
  resourceType: string
  resourceId: string
}>()

const router = useRouter()

const tabs = [
  { key: 'depends', label: '相依資源' },
  { key: 'usedBy',  label: '被誰使用' },
] as const

type TabKey = typeof tabs[number]['key']

const active = ref<TabKey>('depends')
const dependsList = ref<Relation[]>([])
const usedByList  = ref<Relation[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

const current = computed<Relation[]>(() =>
  active.value === 'depends' ? dependsList.value : usedByList.value
)
const counts = computed<Record<TabKey, number>>(() => ({
  depends: dependsList.value.length,
  usedBy:  usedByList.value.length,
}))

const ICON_MAP: Record<string, string> = {
  application:    'message-square',
  knowledge_base: 'book-open',
  tool:           'settings',
  skill:          'key',
  model:          'database',
  mcp_server:     'globe',
  workflow:       'refresh',
}

const LABEL_MAP: Record<string, string> = {
  application:    '應用程式',
  knowledge_base: '知識庫',
  tool:           '工具',
  skill:          '技能',
  model:          '模型',
  mcp_server:     'MCP 伺服器',
  workflow:       '工作流程',
}

function iconFor(t: string)  { return ICON_MAP[t] || 'info' }
function labelFor(t: string) { return LABEL_MAP[t] || t }

function goto(item: Relation) {
  if (!item.url) return
  router.push(item.url).catch(() => { /* 同頁路由忽略 */ })
}

async function load() {
  if (!props.resourceType || !props.resourceId) return
  loading.value = true
  error.value = null
  try {
    const base = `/resources/${props.resourceType}/${props.resourceId}`
    const [dep, used] = await Promise.all([
      http.get(`${base}/depends-on`),
      http.get(`${base}/used-by`),
    ])
    dependsList.value = (dep.data?.data ?? []) as Relation[]
    usedByList.value  = (used.data?.data ?? []) as Relation[]
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || '載入失敗'
    dependsList.value = []
    usedByList.value = []
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.resourceType, props.resourceId],
  () => load(),
  { immediate: true },
)
</script>
