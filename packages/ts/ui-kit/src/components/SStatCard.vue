<template>
  <div class="bg-surface-raised rounded-xl border border-neutral-200 p-5 hover:border-neutral-300 transition-colors">
    <div class="flex items-start justify-between">
      <div class="min-w-0">
        <p class="text-xs text-neutral-500">{{ label }}</p>
        <p class="mt-1 text-2xl font-semibold text-fg tabular-nums truncate">{{ formattedValue }}</p>
        <p v-if="hint" class="mt-1 text-[11px] text-neutral-400">{{ hint }}</p>
      </div>
      <div v-if="$slots.icon || icon"
           :class="['w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0', toneBg]">
        <slot name="icon"><span class="text-base">{{ icon }}</span></slot>
      </div>
    </div>
    <div v-if="trend !== undefined" class="mt-3 flex items-center gap-1 text-[11px]">
      <span :class="trend >= 0 ? 'text-success-600' : 'text-danger-600'">
        {{ trend >= 0 ? '↑' : '↓' }} {{ Math.abs(trend) }}%
      </span>
      <span class="text-neutral-400">vs 上期</span>
    </div>
    <slot name="footer"/>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
const props = withDefaults(defineProps<{
  label:  string
  value:  number | string
  hint?:  string
  icon?:  string
  tone?:  'brand' | 'success' | 'warning' | 'danger' | 'neutral'
  trend?: number
  format?: 'number' | 'currency' | 'percent' | 'raw'
  currency?: string
}>(), { tone: 'neutral', format: 'raw', currency: 'USD' })

const toneBg = computed(() => ({
  brand:   'bg-brand-50  text-brand-600',
  success: 'bg-success-50 text-success-600',
  warning: 'bg-warning-50 text-warning-600',
  danger:  'bg-danger-50 text-danger-600',
  neutral: 'bg-neutral-100 text-neutral-600',
}[props.tone]))

const formattedValue = computed(() => {
  if (typeof props.value === 'string') return props.value
  if (props.format === 'number')   return props.value.toLocaleString('zh-TW')
  if (props.format === 'currency') return new Intl.NumberFormat('zh-TW', { style: 'currency', currency: props.currency }).format(props.value)
  if (props.format === 'percent')  return `${props.value}%`
  return String(props.value)
})
</script>
