<template>
  <label :class="['inline-flex items-center gap-2 cursor-pointer select-none', disabled ? 'opacity-50 cursor-not-allowed' : '']">
    <input type="radio" :name="name" :value="value" :checked="modelValue === value" :disabled="disabled"
           @change="emit('update:modelValue', value)" class="peer sr-only"/>
    <span :class="[
      'flex items-center justify-center w-4 h-4 rounded-full border-[1.5px] transition-all',
      modelValue === value
        ? 'bg-surface-raised border-brand-600'
        : 'bg-surface-raised border-neutral-300 hover:border-neutral-400 peer-focus-visible:ring-2 peer-focus-visible:ring-brand-300',
    ]">
      <span v-if="modelValue === value" class="w-2 h-2 rounded-full bg-brand-600"/>
    </span>
    <span v-if="$slots.default || label" class="text-sm text-fg"><slot>{{ label }}</slot></span>
  </label>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: string | number | boolean
  value:      string | number | boolean
  name?:      string
  label?:     string
  disabled?:  boolean
}>()
const emit = defineEmits<{ (e: 'update:modelValue', v: any): void }>()
</script>
