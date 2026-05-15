<template>
  <svg :class="classes" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" role="status" aria-label="載入中">
    <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-opacity="0.2" stroke-width="3" />
    <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" stroke-width="3" stroke-linecap="round" />
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
}>(), { size: 'md' })

const sizeMap: Record<string, string> = {
  xs: 'w-3 h-3',
  sm: 'w-4 h-4',
  md: 'w-5 h-5',
  lg: 'w-6 h-6',
  xl: 'w-8 h-8',
}

const classes = computed(() => ['animate-spin', sizeMap[props.size]])
</script>
