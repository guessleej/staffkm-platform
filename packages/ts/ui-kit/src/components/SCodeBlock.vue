<template>
  <div class="relative group rounded-lg bg-neutral-900 text-neutral-100 overflow-hidden">
    <div v-if="lang || $slots.toolbar" class="flex items-center justify-between px-3 py-1.5 text-[10px] text-neutral-400 bg-neutral-800/50 border-b border-neutral-700/50 uppercase tracking-wider">
      <span>{{ lang }}</span>
      <button @click="copy"
              class="opacity-60 hover:opacity-100 transition px-2 py-0.5 rounded text-[10px]"
              :title="copied ? '已複製' : '複製'">
        {{ copied ? '✓ 已複製' : '複製' }}
      </button>
    </div>
    <pre class="px-4 py-3 text-[12px] font-mono whitespace-pre-wrap leading-relaxed overflow-x-auto"><code><slot>{{ code }}</slot></code></pre>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
const props = defineProps<{ code?: string; lang?: string }>()
const copied = ref(false)
async function copy() {
  const text = props.code ?? ''
  try {
    await navigator.clipboard.writeText(text)
    copied.value = true
    setTimeout(() => (copied.value = false), 1500)
  } catch { /* ignore */ }
}
</script>
