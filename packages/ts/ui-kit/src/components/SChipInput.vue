<template>
  <div :class="['flex items-center flex-wrap gap-1.5 min-h-9 px-2 py-1 rounded-lg border bg-surface-raised',
                focused ? 'border-brand-400 ring-2 ring-brand-100' : 'border-neutral-200']"
       @click="$refs.input?.focus()">
    <span v-for="(chip, i) in modelValue" :key="i"
          class="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-brand-50 text-brand-700 rounded">
      {{ chip }}
      <button @click.stop="remove(i)" class="ml-0.5 text-brand-400 hover:text-brand-700" aria-label="移除">×</button>
    </span>
    <input ref="input" v-model="draft" type="text" :placeholder="modelValue.length ? '' : placeholder"
           class="flex-1 min-w-[80px] outline-none border-none bg-transparent text-sm text-fg placeholder:text-neutral-400 py-0.5"
           @keydown.enter.prevent="add" @keydown.tab.prevent="add"
           @keydown.backspace="onBackspace"
           @focus="focused = true" @blur="focused = false"
           autocomplete="off"/>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  modelValue: string[]
  placeholder?: string
}>()
const emit = defineEmits<{ (e: 'update:modelValue', v: string[]): void }>()

const draft = ref('')
const focused = ref(false)
const input = ref<HTMLInputElement>()

function add() {
  const v = draft.value.trim()
  if (!v) return
  if (props.modelValue.includes(v)) { draft.value = ''; return }
  emit('update:modelValue', [...props.modelValue, v])
  draft.value = ''
}
function remove(i: number) {
  const arr = props.modelValue.slice()
  arr.splice(i, 1)
  emit('update:modelValue', arr)
}
function onBackspace() {
  if (draft.value === '' && props.modelValue.length) {
    remove(props.modelValue.length - 1)
  }
}
</script>
