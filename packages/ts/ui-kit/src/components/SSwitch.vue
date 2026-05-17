<template>
  <button type="button"
          role="switch" :aria-checked="modelValue" :disabled="disabled"
          @click="onClick"
          :class="[
            'inline-flex items-center transition-colors rounded-full',
            size === 'sm' ? 'h-4 w-7' : 'h-5 w-9',
            modelValue ? 'bg-brand-600' : 'bg-neutral-300',
            disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-300 focus-visible:ring-offset-1',
          ]">
    <span :class="[
      'inline-block bg-white rounded-full shadow-sm transform transition-transform',
      size === 'sm' ? 'w-3 h-3 ml-0.5' : 'w-4 h-4 ml-0.5',
      modelValue ? (size === 'sm' ? 'translate-x-3' : 'translate-x-4') : 'translate-x-0',
    ]"/>
  </button>
</template>

<script setup lang="ts">
const props = defineProps<{
  modelValue: boolean
  disabled?:  boolean
  size?:      'sm' | 'md'
}>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()
function onClick() { if (!props.disabled) emit('update:modelValue', !props.modelValue) }
</script>
