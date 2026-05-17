<template>
  <div class="flex items-center gap-1 text-sm" role="navigation" aria-label="分頁">
    <button @click="go(modelValue - 1)" :disabled="modelValue <= 1"
            class="h-8 w-8 inline-flex items-center justify-center rounded-md text-neutral-500 hover:bg-neutral-100 hover:text-fg disabled:opacity-30 disabled:hover:bg-transparent"
            aria-label="上一頁">‹</button>
    <button v-for="p in pages" :key="p"
            @click="typeof p === 'number' && go(p)"
            :disabled="p === '...'"
            :class="['h-8 min-w-[2rem] px-2 rounded-md font-medium transition',
                     p === modelValue ? 'bg-brand-600 text-white' : 'text-fg hover:bg-neutral-100',
                     p === '...' ? 'cursor-default text-neutral-400' : '']">{{ p }}</button>
    <button @click="go(modelValue + 1)" :disabled="modelValue >= totalPages"
            class="h-8 w-8 inline-flex items-center justify-center rounded-md text-neutral-500 hover:bg-neutral-100 hover:text-fg disabled:opacity-30 disabled:hover:bg-transparent"
            aria-label="下一頁">›</button>
    <span class="ml-3 text-xs text-neutral-400">共 {{ total }} 筆</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{
  modelValue: number
  total:      number
  pageSize:   number
}>()
const emit = defineEmits<{ (e: 'update:modelValue', v: number): void }>()
const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))
const pages = computed<(number | '...')[]>(() => {
  const p = props.modelValue
  const last = totalPages.value
  if (last <= 7) return Array.from({ length: last }, (_, i) => i + 1)
  const out: (number | '...')[] = [1]
  if (p > 3) out.push('...')
  for (let i = Math.max(2, p - 1); i <= Math.min(last - 1, p + 1); i++) out.push(i)
  if (p < last - 2) out.push('...')
  out.push(last)
  return out
})
function go(n: number) {
  if (n < 1 || n > totalPages.value) return
  emit('update:modelValue', n)
}
</script>
