<template>
  <nav class="flex items-center text-sm text-neutral-500" aria-label="breadcrumb">
    <ol class="flex items-center gap-1.5">
      <li v-for="(it, i) in items" :key="i" class="flex items-center gap-1.5">
        <component :is="it.to ? 'router-link' : 'span'" :to="it.to"
                   :class="['transition truncate max-w-[200px]',
                            it.to ? 'hover:text-brand-600 cursor-pointer' : 'text-fg font-medium']">
          {{ it.label }}
        </component>
        <svg v-if="i < items.length - 1" class="w-3 h-3 text-neutral-300 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
        </svg>
      </li>
    </ol>
  </nav>
</template>

<script setup lang="ts">
defineProps<{ items: { label: string; to?: string | object }[] }>()
</script>
