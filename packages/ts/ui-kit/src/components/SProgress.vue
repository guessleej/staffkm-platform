<template>
  <div v-if="!circular" :class="['relative w-full overflow-hidden rounded-full bg-neutral-100', heightCls]">
    <div :class="['h-full transition-all duration-300 rounded-full', colorCls]"
         :style="{ width: pct + '%' }" role="progressbar" :aria-valuenow="pct" aria-valuemin="0" aria-valuemax="100"/>
  </div>
  <svg v-else :class="['inline-block', sizeCls]" viewBox="0 0 36 36" role="progressbar" :aria-valuenow="pct">
    <circle cx="18" cy="18" r="16" fill="none" stroke="hsl(var(--color-neutral-200))" stroke-width="3"/>
    <circle cx="18" cy="18" r="16" fill="none" :stroke="strokeColor" stroke-width="3"
            stroke-dasharray="100" :stroke-dashoffset="100 - pct"
            stroke-linecap="round" transform="rotate(-90 18 18)"
            class="transition-all duration-300"/>
    <text v-if="showLabel" x="18" y="20" text-anchor="middle" font-size="9" fill="hsl(var(--color-text-secondary))">
      {{ pct }}%
    </text>
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'
const props = withDefaults(defineProps<{
  value: number
  max?: number
  tone?: 'brand' | 'success' | 'warning' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  circular?: boolean
  showLabel?: boolean
}>(), { max: 100, tone: 'brand', size: 'md' })
const pct = computed(() => Math.max(0, Math.min(100, Math.round((props.value / props.max) * 100))))
const heightCls = computed(() => props.size === 'sm' ? 'h-1' : props.size === 'lg' ? 'h-3' : 'h-2')
const colorCls = computed(() => ({ brand: 'bg-brand-500', success: 'bg-success-500', warning: 'bg-warning-500', danger: 'bg-danger-500' }[props.tone]))
const sizeCls = computed(() => props.size === 'sm' ? 'w-8 h-8' : props.size === 'lg' ? 'w-16 h-16' : 'w-12 h-12')
const strokeColor = computed(() => ({ brand: 'hsl(var(--color-brand-500))', success: 'hsl(var(--color-success-500))', warning: 'hsl(var(--color-warning-500))', danger: 'hsl(var(--color-danger-500))' }[props.tone]))
</script>
