<template>
  <transition
    enter-active-class="transition-transform duration-300 ease-out"
    enter-from-class="translate-x-full"
    leave-active-class="transition-transform duration-200 ease-in"
    leave-to-class="translate-x-full"
  >
    <aside
      v-if="store.isOpen && a"
      class="w-[480px] flex flex-col bg-surface-raised border-l border-neutral-200 flex-shrink-0 overflow-hidden"
    >
      <!-- 標題列 -->
      <header class="h-12 px-4 flex items-center justify-between border-b border-neutral-100 flex-shrink-0">
        <div class="flex items-center gap-2 min-w-0">
          <span class="text-[10px] uppercase tracking-widest text-neutral-400 flex-shrink-0">
            {{ kindLabel }}
          </span>
          <span class="text-sm font-medium text-neutral-900 truncate">{{ a.title }}</span>
        </div>
        <button
          @click="store.close()"
          class="w-8 h-8 flex items-center justify-center rounded-lg text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900 transition flex-shrink-0"
          :title="$t('common.cancel')"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </header>

      <!-- 內容區（依 kind 分派渲染）-->
      <div class="flex-1 overflow-y-auto">
        <!-- document：純文字 / markdown 預覽 -->
        <article
          v-if="a.kind === 'document'"
          class="px-5 py-4 text-[14px] leading-7 text-neutral-800 whitespace-pre-wrap"
        >{{ a.content }}</article>

        <!-- code：等寬字 + 灰底 -->
        <pre
          v-else-if="a.kind === 'code'"
          class="px-5 py-4 text-[13px] leading-6 font-mono text-neutral-800 bg-neutral-50 whitespace-pre overflow-x-auto"
        ><code>{{ a.content }}</code></pre>

        <!-- image -->
        <div v-else-if="a.kind === 'image'" class="p-4 flex items-center justify-center">
          <img :src="a.src" :alt="a.alt || a.title" class="max-w-full max-h-[80vh] rounded-md" />
        </div>

        <!-- iframe（外部頁面內嵌；只允許 https / 同源）-->
        <iframe
          v-else-if="a.kind === 'iframe'"
          :src="a.src"
          class="w-full h-full border-0"
          sandbox="allow-scripts allow-same-origin"
        />

        <!-- workflow：暫以節點數量摘要（後續可接 LogicFlow mini-preview）-->
        <div v-else-if="a.kind === 'workflow'" class="px-5 py-4 text-sm text-neutral-700">
          <p class="text-neutral-500 mb-3">Workflow 預覽（待接 LogicFlow mini renderer）</p>
          <ul class="space-y-1 text-xs font-mono">
            <li v-for="n in a.nodes" :key="n.id">
              {{ n.node_type }} · {{ n.node_key }}
            </li>
          </ul>
          <p class="mt-3 text-xs text-neutral-400">
            {{ a.nodes.length }} 節點 · {{ a.edges.length }} 連線
          </p>
        </div>
      </div>
    </aside>
  </transition>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useArtifactStore } from '../../stores/artifact'

const store = useArtifactStore()
const { t } = useI18n()

// 解構取當前 artifact（透過 computed 避免 null 解構 crash）
const a = computed(() => store.current)

const kindLabel = computed(() => {
  switch (a.value?.kind) {
    case 'document': return 'DOC'
    case 'code':     return 'CODE'
    case 'image':    return 'IMG'
    case 'workflow': return 'FLOW'
    case 'iframe':   return 'WEB'
    default:         return ''
  }
})

// 抑制未用警告
void t
</script>
