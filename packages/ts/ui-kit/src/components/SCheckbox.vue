<template>
  <label :class="['inline-flex items-center gap-2 cursor-pointer select-none', disabled ? 'opacity-50 cursor-not-allowed' : '']">
    <input
      type="checkbox"
      :checked="modelValue"
      :disabled="disabled"
      :indeterminate.prop="indeterminate"
      @change="onChange"
      class="peer sr-only"
    />
    <span :class="[
      'flex items-center justify-center w-4 h-4 rounded border-[1.5px] transition-all',
      modelValue || indeterminate
        ? 'bg-brand-600 border-brand-600 text-white'
        : 'bg-surface-raised border-neutral-300 hover:border-neutral-400 peer-focus-visible:ring-2 peer-focus-visible:ring-brand-300',
    ]">
      <svg v-if="modelValue && !indeterminate" class="w-3 h-3" viewBox="0 0 16 16" fill="none">
        <path d="M3 8l3 3 7-7" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <span v-else-if="indeterminate" class="w-2 h-0.5 bg-white rounded"/>
    </span>
    <span v-if="$slots.default || label" class="text-sm text-fg"><slot>{{ label }}</slot></span>
  </label>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: boolean
  label?: string
  disabled?: boolean
  indeterminate?: boolean
}>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()
function onChange(e: Event) { emit('update:modelValue', (e.target as HTMLInputElement).checked) }
</script>
