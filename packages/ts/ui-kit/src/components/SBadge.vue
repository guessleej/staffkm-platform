<template>
  <span :class="classes">
    <span v-if="dot" :class="dotClasses" />
    <slot />
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  intent?: 'neutral' | 'brand' | 'success' | 'warning' | 'danger' | 'info'
  size?:   'sm' | 'md'
  variant?: 'subtle' | 'solid' | 'outline'
  dot?:    boolean
}>(), {
  intent:  'neutral',
  size:    'sm',
  variant: 'subtle',
})

const variantMap: Record<string, Record<string, string>> = {
  subtle: {
    neutral: 'bg-neutral-100 text-neutral-700',
    brand:   'bg-brand-50 text-brand-700',
    success: 'bg-success-50 text-success-700',
    warning: 'bg-warning-50 text-warning-700',
    danger:  'bg-danger-50 text-danger-700',
    info:    'bg-info-50 text-info-700',
  },
  solid: {
    neutral: 'bg-neutral-700 text-white',
    brand:   'bg-brand-600 text-white',
    success: 'bg-success-600 text-white',
    warning: 'bg-warning-600 text-white',
    danger:  'bg-danger-600 text-white',
    info:    'bg-info-600 text-white',
  },
  outline: {
    neutral: 'border border-neutral-300 text-neutral-700',
    brand:   'border border-brand-300 text-brand-700',
    success: 'border border-success-500 text-success-700',
    warning: 'border border-warning-500 text-warning-700',
    danger:  'border border-danger-500 text-danger-700',
    info:    'border border-info-500 text-info-700',
  },
}
const dotColorMap: Record<string, string> = {
  neutral: 'bg-neutral-500',
  brand:   'bg-brand-500',
  success: 'bg-success-500',
  warning: 'bg-warning-500',
  danger:  'bg-danger-500',
  info:    'bg-info-500',
}

const classes = computed(() => [
  'inline-flex items-center gap-1 font-medium rounded-full whitespace-nowrap',
  props.size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-0.5 text-xs',
  variantMap[props.variant][props.intent],
])
const dotClasses = computed(() => [
  'w-1.5 h-1.5 rounded-full',
  dotColorMap[props.intent],
])
</script>
