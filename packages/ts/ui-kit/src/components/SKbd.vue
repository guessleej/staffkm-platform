<template>
  <span class="inline-flex items-center gap-0.5 align-middle">
    <kbd v-for="(k, i) in keys" :key="i"
         class="inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1 text-[10px] font-mono
                bg-surface-raised border border-neutral-200 rounded text-neutral-600 shadow-sm">
      {{ k }}
    </kbd>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ k: string | string[] }>()
const keys = computed(() => Array.isArray(props.k) ? props.k : props.k.split('+').map(s => s.trim()))
</script>
