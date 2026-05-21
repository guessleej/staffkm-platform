<template>
  <div
    class="flex items-end gap-2 rounded-2xl border border-neutral-200 bg-surface-raised shadow-sm px-3 py-2 transition focus-within:border-brand-400 focus-within:shadow"
  >
    <textarea
      ref="taRef"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      rows="1"
      class="flex-1 resize-none bg-transparent outline-none text-[15px] leading-6 text-neutral-900 placeholder:text-neutral-400 max-h-48"
      @input="onInput"
      @keydown.enter.exact="onEnterKey"
    />
    <button
      type="button"
      class="w-9 h-9 flex items-center justify-center rounded-xl bg-brand-600 text-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-brand-700 transition flex-shrink-0"
      :disabled="disabled || !canSubmit"
      title="送出（Enter）"
      @click="submit"
    >
      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14M13 6l6 6-6 6"/>
      </svg>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps<{
  modelValue: string
  placeholder?: string
  disabled?: boolean
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: string): void
  (e: 'submit'): void
}>()

const taRef = ref<HTMLTextAreaElement | null>(null)

const canSubmit = computed(() => props.modelValue.trim().length > 0)

function onInput(e: Event) {
  const v = (e.target as HTMLTextAreaElement).value
  emit('update:modelValue', v)
  autoResize()
}
function submit() {
  if (!canSubmit.value || props.disabled) return
  emit('submit')
}
// v5.9.29: IME 組字中按 Enter (選字確認) 不送出
function onEnterKey(e: KeyboardEvent) {
  if (e.isComposing || (e as any).keyCode === 229) return
  e.preventDefault()
  submit()
}

function autoResize() {
  const el = taRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 192) + 'px'
}

watch(() => props.modelValue, () => nextTick(autoResize))
</script>
