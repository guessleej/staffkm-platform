<template>
  <label
    :class="['relative block rounded-xl border-2 border-dashed transition-colors cursor-pointer',
             dragging ? 'border-brand-400 bg-brand-50/40' : 'border-neutral-300 hover:border-neutral-400 hover:bg-neutral-50/50',
             'px-6 py-10 text-center']"
    @dragover.prevent="dragging = true"
    @dragenter.prevent="dragging = true"
    @dragleave="dragging = false"
    @drop.prevent="onDrop"
  >
    <input ref="input" type="file" :accept="accept" :multiple="multiple" class="sr-only" @change="onFile"/>
    <div class="flex flex-col items-center gap-2">
      <svg class="w-8 h-8 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M17 8l-5-5-5 5M12 3v12"/>
      </svg>
      <p class="text-sm font-medium text-fg">
        <span class="text-brand-600">點擊上傳</span> 或拖曳檔案至此
      </p>
      <p v-if="hint" class="text-xs text-neutral-400">{{ hint }}</p>
    </div>
  </label>
</template>

<script setup lang="ts">
import { ref } from 'vue'
const props = defineProps<{
  accept?: string
  multiple?: boolean
  hint?: string
}>()
const emit = defineEmits<{ (e: 'select', files: File[]): void }>()
const dragging = ref(false)
const input = ref<HTMLInputElement>()
function onFile(e: Event) {
  const files = Array.from((e.target as HTMLInputElement).files || [])
  if (files.length) emit('select', files)
  if (input.value) input.value.value = ''
}
function onDrop(e: DragEvent) {
  dragging.value = false
  const files = Array.from(e.dataTransfer?.files || [])
  if (files.length) emit('select', files)
}
</script>
