<template>
  <div class="relative">
    <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-neutral-400 pointer-events-none"
         fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
      <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z"/>
    </svg>
    <input
      :value="modelValue"
      type="search"
      :placeholder="placeholder || '搜尋…'"
      :class="['w-full h-9 pl-9 pr-9 text-sm rounded-lg border border-neutral-200 bg-surface-raised text-fg',
               'placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-300 focus:border-brand-400',
               'transition-colors']"
      @input="onInput"
      @keydown.esc="clear"
      autocomplete="off"
    />
    <button v-if="modelValue" @click="clear"
            class="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-neutral-300 hover:text-neutral-600 rounded"
            aria-label="清除">
      <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
      </svg>
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{ modelValue: string; placeholder?: string }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: string): void
}>()
function onInput(e: Event) { emit('update:modelValue', (e.target as HTMLInputElement).value) }
function clear() { emit('update:modelValue', '') }
</script>
