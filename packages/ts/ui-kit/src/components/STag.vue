<template>
  <span :class="classes">
    <slot />
    <button
      v-if="closable"
      type="button"
      class="ml-1 -mr-0.5 hover:bg-black/10 rounded-full p-0.5 transition-colors"
      @click.stop="$emit('close')"
    >
      <svg class="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
      </svg>
    </button>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  intent?: 'neutral' | 'brand' | 'success' | 'warning' | 'danger' | 'info'
  closable?: boolean
}>(), { intent: 'neutral' })

defineEmits<{ close: [] }>()

const intentMap: Record<string, string> = {
  neutral: 'bg-neutral-100 text-neutral-700 border border-neutral-200',
  brand:   'bg-brand-50 text-brand-700 border border-brand-200',
  success: 'bg-success-50 text-success-700 border border-success-500/30',
  warning: 'bg-warning-50 text-warning-700 border border-warning-500/30',
  danger:  'bg-danger-50 text-danger-700 border border-danger-500/30',
  info:    'bg-info-50 text-info-700 border border-info-500/30',
}
const classes = computed(() => [
  'inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-md',
  intentMap[props.intent],
])
</script>
