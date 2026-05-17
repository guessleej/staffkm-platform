<template>
  <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200 bg-surface-raised flex-shrink-0">
    <div class="flex items-center gap-3 min-w-0">
      <slot name="back"/>
      <div class="min-w-0">
        <h1 v-if="title" class="text-base font-semibold text-fg truncate">{{ title }}</h1>
        <p v-if="subtitle" class="text-xs text-neutral-500 mt-0.5 truncate">{{ subtitle }}</p>
        <slot name="header"/>
      </div>
    </div>
    <div class="flex items-center gap-2 flex-shrink-0">
      <slot/>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ title?: string; subtitle?: string }>()
</script>
