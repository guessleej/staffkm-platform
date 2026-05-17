<template>
  <div class="relative inline-block w-full">
    <select
      :value="modelValue"
      :disabled="disabled"
      @change="emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
      :class="[
        'w-full appearance-none rounded-lg border border-neutral-200 bg-surface-raised text-sm text-fg',
        'pl-3 pr-9 h-9 cursor-pointer',
        'focus:outline-none focus:ring-2 focus:ring-brand-300 focus:border-brand-400',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        'transition-colors',
      ]">
      <option v-if="placeholder" value="" disabled>{{ placeholder }}</option>
      <slot>
        <option v-for="o in options" :key="o.value" :value="o.value">{{ o.label }}</option>
      </slot>
    </select>
    <svg class="absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-neutral-400 pointer-events-none"
         fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
      <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/>
    </svg>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: string | number
  options?:   { label: string; value: string | number }[]
  placeholder?: string
  disabled?:  boolean
}>()
const emit = defineEmits<{ (e: 'update:modelValue', v: string | number): void }>()
</script>
