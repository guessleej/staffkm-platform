<template>
  <div :class="containerClasses">
    <div v-if="$slots.header || title" class="px-5 py-3 border-b border-neutral-100 flex items-center justify-between">
      <div class="min-w-0">
        <slot name="header">
          <h3 class="text-sm font-semibold text-neutral-900 truncate">{{ title }}</h3>
          <p v-if="subtitle" class="text-xs text-neutral-500 mt-0.5">{{ subtitle }}</p>
        </slot>
      </div>
      <div v-if="$slots.actions" class="flex items-center gap-2">
        <slot name="actions" />
      </div>
    </div>
    <div :class="bodyClasses">
      <slot />
    </div>
    <div v-if="$slots.footer" class="px-5 py-3 border-t border-neutral-100 flex items-center justify-end gap-2">
      <slot name="footer" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  title?:    string
  subtitle?: string
  variant?:  'default' | 'flat' | 'elevated'
  padding?:  'none' | 'sm' | 'md' | 'lg'
  hoverable?: boolean
}>(), {
  variant: 'default',
  padding: 'md',
})

const containerClasses = computed(() => [
  'bg-surface-raised rounded-xl overflow-hidden',
  props.variant === 'default'  ? 'border border-neutral-200' : '',
  props.variant === 'elevated' ? 'shadow-md' : '',
  props.variant === 'flat'     ? '' : '',
  props.hoverable ? 'transition-shadow duration-base hover:shadow-lg cursor-pointer' : '',
])

const bodyClasses = computed(() => ({
  none: '',
  sm:   'px-3 py-2',
  md:   'px-5 py-4',
  lg:   'px-6 py-5',
}[props.padding]))
</script>
