<template>
  <div class="mb-4 bg-surface-raised border border-bd rounded-xl overflow-hidden">
    <button
      @click="open = !open"
      class="w-full flex items-center justify-between px-4 py-2.5 text-left hover:bg-neutral-50 transition"
    >
      <span class="text-xs font-semibold text-fg flex items-center gap-2">
        <SIcon name="info" :size="14" class="text-brand-600 shrink-0" />
        {{ title }}
      </span>
      <span class="text-[11px] text-fg-tertiary shrink-0 ml-2">{{ open ? '收合 ▲' : '說明 ▼' }}</span>
    </button>
    <div v-if="open" class="px-4 pb-4 pt-3 text-xs text-fg-secondary leading-relaxed border-t border-bd space-y-2">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { SIcon } from '@staffkm/ui-kit'

defineProps<{ title: string }>()
const open = ref(false)   // admin 頁預設收合，標題常駐、點「說明 ▼」展開
</script>
