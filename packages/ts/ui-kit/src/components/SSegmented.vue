<template>
  <div class="inline-flex p-0.5 rounded-lg bg-neutral-100 border border-neutral-200" role="group">
    <button v-for="o in options" :key="String(o.value)"
            @click="emit('update:modelValue', o.value)"
            :class="['px-3 py-1 text-xs font-medium rounded-md transition',
                     modelValue === o.value ? 'bg-surface-raised text-fg shadow-sm' : 'text-neutral-500 hover:text-fg']">
      {{ o.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: string | number
  options: { label: string; value: string | number }[]
}>()
const emit = defineEmits<{ (e: 'update:modelValue', v: string | number): void }>()
</script>
