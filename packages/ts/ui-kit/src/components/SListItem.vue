<template>
  <component :is="to ? 'router-link' : 'div'" :to="to"
             :class="['flex items-center gap-3 px-3 py-2 rounded-lg transition-colors group',
                      active ? 'bg-brand-50 text-brand-700' : 'text-fg hover:bg-neutral-50',
                      disabled ? 'opacity-40 cursor-not-allowed pointer-events-none' : 'cursor-pointer']">
    <div v-if="$slots.icon" class="flex-shrink-0 text-base"><slot name="icon"/></div>
    <div class="flex-1 min-w-0">
      <p class="text-sm font-medium truncate"><slot>{{ title }}</slot></p>
      <p v-if="subtitle" class="text-[11px] text-neutral-500 truncate">{{ subtitle }}</p>
    </div>
    <div v-if="$slots.trailing" class="flex-shrink-0 text-[11px] text-neutral-400"><slot name="trailing"/></div>
  </component>
</template>

<script setup lang="ts">
defineProps<{
  title?: string
  subtitle?: string
  to?: string | object
  active?: boolean
  disabled?: boolean
}>()
</script>
