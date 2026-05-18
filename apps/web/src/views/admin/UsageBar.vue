<template>
  <div>
    <div class="flex items-center justify-between text-xs mb-1">
      <span class="font-mono tabular-nums text-fg">{{ formatUsed }}</span>
      <span class="text-fg-tertiary">/ {{ formatCap }}</span>
    </div>
    <div class="h-1.5 w-full rounded-full bg-neutral-100 overflow-hidden">
      <div class="h-full rounded-full transition-all"
           :class="barClass"
           :style="{ width: Math.min(100, pct) + '%' }"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  used: number
  cap: number | null
  formatAsCost?: boolean
}>()

const pct = computed(() => {
  if (!props.cap || props.cap <= 0) return 0
  return (Number(props.used) / Number(props.cap)) * 100
})

const barClass = computed(() => {
  if (pct.value >= 90) return 'bg-danger-500'
  if (pct.value >= 70) return 'bg-warning-500'
  return 'bg-success-500'
})

function fmt(n: number | null | undefined, isInfinity = false): string {
  if (isInfinity) return '∞'
  if (n === null || n === undefined) return '—'
  if (props.formatAsCost) return '$' + Number(n).toFixed(props.cap === null ? 4 : 2)
  return Number(n).toLocaleString('zh-TW')
}

const formatUsed = computed(() => {
  if (props.formatAsCost) return '$' + Number(props.used).toFixed(4)
  return Number(props.used).toLocaleString('zh-TW')
})

const formatCap = computed(() => {
  if (props.cap === null || props.cap === undefined) return '∞'
  return fmt(props.cap)
})
</script>
