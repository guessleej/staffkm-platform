<template>
  <div :class="containerClasses">
    <div class="opacity-50 mb-4" :class="iconWrapperClasses">
      <slot name="icon">
        <svg class="w-full h-full" fill="none" viewBox="0 0 64 64" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M8 16l4-8h40l4 8M8 16h48v32a4 4 0 0 1-4 4H12a4 4 0 0 1-4-4V16zm12 12h24" />
        </svg>
      </slot>
    </div>
    <h3 v-if="title" class="text-sm font-semibold text-neutral-700 mb-1">{{ title }}</h3>
    <p v-if="description" class="text-xs text-neutral-500 max-w-md">{{ description }}</p>
    <div v-if="$slots.action" class="mt-4">
      <slot name="action" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  title?:       string
  description?: string
  size?:        'sm' | 'md' | 'lg'
}>(), { size: 'md' })

const containerClasses = computed(() => [
  'flex flex-col items-center justify-center text-center',
  props.size === 'sm' ? 'py-8'  : props.size === 'lg' ? 'py-20' : 'py-14',
])
const iconWrapperClasses = computed(() => ({
  sm: 'w-10 h-10 text-neutral-400',
  md: 'w-14 h-14 text-neutral-400',
  lg: 'w-20 h-20 text-neutral-400',
}[props.size]))
</script>
