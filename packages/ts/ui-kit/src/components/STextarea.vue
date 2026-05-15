<template>
  <div class="w-full">
    <label v-if="label" :for="id" class="block text-xs font-semibold text-neutral-600 mb-1">
      {{ label }} <span v-if="required" class="text-danger-600">*</span>
    </label>
    <textarea
      :id="id"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      :readonly="readonly"
      :required="required"
      :rows="rows"
      :class="classes"
      @input="$emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
    />
    <div class="flex items-center justify-between mt-1">
      <p v-if="error" class="text-xs text-danger-600">{{ error }}</p>
      <p v-else-if="hint" class="text-xs text-neutral-500">{{ hint }}</p>
      <p v-if="maxLength" class="text-xs text-neutral-400 ml-auto">
        {{ String(modelValue ?? '').length }} / {{ maxLength }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  modelValue?: string
  rows?:       number
  label?:      string
  placeholder?: string
  hint?:       string
  error?:      string
  disabled?:   boolean
  readonly?:   boolean
  required?:   boolean
  resize?:     'none' | 'both' | 'horizontal' | 'vertical'
  maxLength?:  number
  id?:         string
}>(), {
  rows: 3,
  resize: 'vertical',
})

defineEmits<{ 'update:modelValue': [value: string] }>()

const classes = computed(() => [
  'w-full px-3 py-2 text-sm bg-surface-raised text-neutral-900 placeholder:text-neutral-400',
  'border border-neutral-200 rounded-lg',
  'focus:outline-none focus:border-brand-500 focus:shadow-focus',
  'disabled:bg-neutral-50 disabled:text-neutral-400 disabled:cursor-not-allowed',
  'transition-colors duration-fast',
  `resize-${props.resize}`,
  props.error ? 'border-danger-500 focus:border-danger-500' : '',
])
</script>
