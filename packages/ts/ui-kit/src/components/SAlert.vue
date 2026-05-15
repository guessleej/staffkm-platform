<template>
  <div :class="classes" role="alert">
    <div class="flex-shrink-0 mt-0.5" :class="iconColor">
      <slot name="icon">
        <span class="text-base">{{ defaultIcon }}</span>
      </slot>
    </div>
    <div class="flex-1 min-w-0">
      <p v-if="title" class="font-semibold text-sm" :class="titleColor">{{ title }}</p>
      <div class="text-xs mt-0.5" :class="bodyColor">
        <slot />
      </div>
    </div>
    <button
      v-if="closable"
      type="button"
      class="ml-auto -mr-1 -mt-1 p-1 rounded-md hover:bg-black/5 transition-colors flex-shrink-0"
      :class="iconColor"
      @click="$emit('close')"
    >
      <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
      </svg>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  intent?: 'info' | 'success' | 'warning' | 'danger'
  title?:  string
  closable?: boolean
}>(), { intent: 'info' })

defineEmits<{ close: [] }>()

const intentBg: Record<string, string> = {
  info:    'bg-info-50    border-info-500/30',
  success: 'bg-success-50 border-success-500/30',
  warning: 'bg-warning-50 border-warning-500/30',
  danger:  'bg-danger-50  border-danger-500/30',
}
const iconColorMap: Record<string, string> = {
  info: 'text-info-600', success: 'text-success-600', warning: 'text-warning-600', danger: 'text-danger-600',
}
const titleColorMap: Record<string, string> = {
  info: 'text-info-700', success: 'text-success-700', warning: 'text-warning-700', danger: 'text-danger-700',
}
const defaultIcons: Record<string, string> = { info: 'ℹ', success: '✓', warning: '⚠', danger: '✕' }

const classes = computed(() => [
  'flex items-start gap-3 p-3 rounded-xl border',
  intentBg[props.intent],
])
const iconColor  = computed(() => iconColorMap[props.intent])
const titleColor = computed(() => titleColorMap[props.intent])
const bodyColor  = computed(() => ({
  info: 'text-info-700', success: 'text-success-700', warning: 'text-warning-700', danger: 'text-danger-700',
}[props.intent]))
const defaultIcon = computed(() => defaultIcons[props.intent])
</script>
