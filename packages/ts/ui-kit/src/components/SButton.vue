<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    :class="classes"
    @click="$emit('click', $event)"
  >
    <SSpinner v-if="loading" :size="iconSize" class="-ml-0.5" />
    <slot name="icon-left" v-else-if="$slots['icon-left']" />
    <span v-if="$slots.default" class="inline-flex items-center"><slot /></span>
    <slot name="icon-right" />
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import SSpinner from './SSpinner.vue'

const props = withDefaults(defineProps<{
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'link'
  size?:    'sm' | 'md' | 'lg'
  type?:    'button' | 'submit' | 'reset'
  block?:   boolean
  loading?: boolean
  disabled?: boolean
}>(), {
  variant: 'primary',
  size:    'md',
  type:    'button',
  block:   false,
  loading: false,
  disabled: false,
})

defineEmits<{ click: [event: MouseEvent] }>()

const iconSize = computed(() => (props.size === 'sm' ? 'xs' : props.size === 'lg' ? 'md' : 'sm'))

const variants: Record<string, string> = {
  primary:   'bg-brand-600 text-white hover:bg-brand-700 active:bg-brand-800 disabled:bg-neutral-300',
  secondary: 'bg-neutral-100 text-neutral-900 hover:bg-neutral-200 active:bg-neutral-300 disabled:bg-neutral-50 disabled:text-neutral-400',
  ghost:     'bg-transparent text-neutral-700 hover:bg-neutral-100 active:bg-neutral-200 disabled:text-neutral-400',
  danger:    'bg-danger-600 text-white hover:bg-danger-700 active:bg-danger-700 disabled:bg-neutral-300',
  link:      'bg-transparent text-brand-600 hover:text-brand-700 hover:underline disabled:text-neutral-400',
}
const sizes: Record<string, string> = {
  sm: 'h-8 px-3 text-xs gap-1.5 rounded-md',
  md: 'h-10 px-4 text-sm gap-2 rounded-lg',
  lg: 'h-12 px-6 text-base gap-2.5 rounded-xl',
}

const classes = computed(() => [
  'inline-flex items-center justify-center font-medium select-none',
  'transition-colors duration-fast ease-out',
  'focus-visible:shadow-focus focus-visible:outline-none',
  'disabled:cursor-not-allowed',
  variants[props.variant],
  sizes[props.size],
  props.block ? 'w-full' : '',
])
</script>
