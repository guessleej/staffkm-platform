<template>
  <div>
    <div :class="['flex items-center border-b border-neutral-200',
                  variant === 'underline' ? 'gap-1' : 'gap-1 p-1 bg-neutral-100 rounded-lg border-0 inline-flex']">
      <button v-for="t in tabs" :key="t.value"
              @click="emit('update:modelValue', t.value)"
              :class="[
                variant === 'underline'
                  ? ['px-3 py-2 text-sm font-medium transition-colors border-b-2 -mb-px',
                     modelValue === t.value
                       ? 'text-brand-600 border-brand-600'
                       : 'text-neutral-500 border-transparent hover:text-fg hover:border-neutral-300']
                  : ['px-3 py-1.5 text-sm font-medium transition rounded-md',
                     modelValue === t.value
                       ? 'bg-surface-raised text-fg shadow-sm'
                       : 'text-neutral-500 hover:text-fg'],
              ]">
        <span v-if="t.icon" class="inline-block mr-1.5">{{ t.icon }}</span>
        {{ t.label }}
        <span v-if="t.badge !== undefined"
              class="ml-1.5 text-[10px] px-1.5 py-0.5 rounded-full bg-neutral-200 text-neutral-600">{{ t.badge }}</span>
      </button>
    </div>
    <div class="pt-3"><slot/></div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: string | number
  tabs: { label: string; value: string | number; icon?: string; badge?: string | number }[]
  variant?: 'underline' | 'pill'
}>()
const emit = defineEmits<{ (e: 'update:modelValue', v: string | number): void }>()
</script>
