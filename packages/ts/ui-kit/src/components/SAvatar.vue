<template>
  <div :class="containerClasses" :style="bgGradientStyle">
    <img v-if="src && !imgError" :src="src" :alt="alt || name" :class="imgClasses" @error="imgError = true" />
    <span v-else-if="name" :class="initialsClasses">{{ initials }}</span>
    <slot v-else />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

const props = withDefaults(defineProps<{
  src?:  string
  name?: string
  alt?:  string
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  shape?: 'circle' | 'rounded' | 'square'
}>(), {
  size: 'md',
  shape: 'circle',
})

const imgError = ref(false)

const initials = computed(() => {
  if (!props.name) return ''
  const parts = props.name.trim().split(/\s+/)
  return parts.length >= 2
    ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
    : props.name.slice(0, 2).toUpperCase()
})

const sizeMap: Record<string, string> = {
  xs: 'w-6 h-6 text-[10px]',
  sm: 'w-8 h-8 text-xs',
  md: 'w-10 h-10 text-sm',
  lg: 'w-12 h-12 text-base',
  xl: 'w-16 h-16 text-lg',
}
const shapeMap: Record<string, string> = {
  circle:  'rounded-full',
  rounded: 'rounded-lg',
  square:  'rounded-none',
}

const containerClasses = computed(() => [
  'inline-flex items-center justify-center overflow-hidden text-white font-semibold flex-shrink-0',
  sizeMap[props.size],
  shapeMap[props.shape],
])
const imgClasses = computed(() => [shapeMap[props.shape], 'w-full h-full object-cover'])
const initialsClasses = computed(() => 'select-none')

// 從 name 派生穩定漸層色
const bgGradientStyle = computed(() => {
  if (props.src && !imgError.value) return undefined
  const seed = props.name || 'X'
  let hash = 0
  for (let i = 0; i < seed.length; i++) hash = (hash << 5) - hash + seed.charCodeAt(i)
  const hue = Math.abs(hash) % 360
  return { background: `linear-gradient(135deg, hsl(${hue},65%,55%), hsl(${(hue + 40) % 360},65%,45%))` }
})
</script>
