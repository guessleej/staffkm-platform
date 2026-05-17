<template>
  <button :type="type" :disabled="disabled"
          :class="['inline-flex items-center justify-center rounded-md transition-colors',
                   sizeCls, toneCls,
                   disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer']"
          :title="title" :aria-label="title">
    <slot/>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
const props = withDefaults(defineProps<{
  size?: 'sm' | 'md' | 'lg'
  tone?: 'neutral' | 'brand' | 'danger'
  variant?: 'ghost' | 'subtle' | 'solid'
  type?: 'button' | 'submit' | 'reset'
  disabled?: boolean
  title?: string
}>(), { size: 'md', tone: 'neutral', variant: 'ghost', type: 'button' })

const sizeCls = computed(() => ({ sm: 'w-7 h-7', md: 'w-8 h-8', lg: 'w-9 h-9' }[props.size]))
const toneCls = computed(() => {
  if (props.variant === 'solid') {
    return ({ neutral: 'bg-neutral-700 text-white hover:bg-neutral-800',
              brand:   'bg-brand-600 text-white hover:bg-brand-700',
              danger:  'bg-danger-600 text-white hover:bg-danger-700' }[props.tone])
  }
  if (props.variant === 'subtle') {
    return ({ neutral: 'bg-neutral-100 text-fg hover:bg-neutral-200',
              brand:   'bg-brand-50 text-brand-700 hover:bg-brand-100',
              danger:  'bg-danger-50 text-danger-700 hover:bg-danger-100' }[props.tone])
  }
  return ({ neutral: 'text-neutral-400 hover:bg-neutral-100 hover:text-fg',
            brand:   'text-neutral-400 hover:bg-brand-50 hover:text-brand-600',
            danger:  'text-neutral-400 hover:bg-danger-50 hover:text-danger-600' }[props.tone])
})
</script>
