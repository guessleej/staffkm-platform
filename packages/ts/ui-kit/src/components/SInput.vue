<template>
  <div class="w-full">
    <label v-if="label" :for="id" class="block text-xs font-semibold text-neutral-600 mb-1">
      {{ label }} <span v-if="required" class="text-danger-600">*</span>
    </label>
    <div class="relative">
      <span v-if="$slots['icon-left']" class="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400">
        <slot name="icon-left" />
      </span>
      <input
        :id="id"
        :value="modelValue"
        :type="type"
        :placeholder="placeholder"
        :disabled="disabled"
        :readonly="readonly"
        :required="required"
        :class="inputClasses"
        @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
        @blur="$emit('blur', $event)"
        @focus="$emit('focus', $event)"
      />
      <span v-if="$slots['icon-right']" class="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400">
        <slot name="icon-right" />
      </span>
    </div>
    <p v-if="error" class="mt-1 text-xs text-danger-600">{{ error }}</p>
    <p v-else-if="hint" class="mt-1 text-xs text-neutral-500">{{ hint }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, useSlots } from 'vue'

const props = withDefaults(defineProps<{
  modelValue?: string | number
  type?:       string
  size?:       'sm' | 'md' | 'lg'
  label?:      string
  placeholder?: string
  hint?:       string
  error?:      string
  disabled?:   boolean
  readonly?:   boolean
  required?:   boolean
  id?:         string
}>(), {
  type: 'text',
  size: 'md',
})

defineEmits<{
  'update:modelValue': [value: string]
  blur:  [event: FocusEvent]
  focus: [event: FocusEvent]
}>()

const slots = useSlots()
const sizes: Record<string, string> = {
  sm: 'h-8 text-xs',
  md: 'h-10 text-sm',
  lg: 'h-12 text-base',
}
const padX = computed(() => {
  const left  = slots['icon-left']  ? 'pl-9' : 'pl-3'
  const right = slots['icon-right'] ? 'pr-9' : 'pr-3'
  return `${left} ${right}`
})
const inputClasses = computed(() => [
  'w-full bg-surface-raised text-neutral-900 placeholder:text-neutral-400',
  'border border-neutral-200 rounded-lg',
  'focus:outline-none focus:border-brand-500 focus:shadow-focus',
  'disabled:bg-neutral-50 disabled:text-neutral-400 disabled:cursor-not-allowed',
  'readonly:bg-neutral-50 readonly:cursor-default',
  'transition-colors duration-fast',
  sizes[props.size],
  padX.value,
  props.error ? 'border-danger-500 focus:border-danger-500' : '',
])
</script>
