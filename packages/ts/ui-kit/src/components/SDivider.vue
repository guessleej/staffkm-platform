<template>
  <div v-if="vertical" class="inline-block w-px self-stretch bg-neutral-200 mx-2"/>
  <div v-else class="flex items-center my-3" role="separator">
    <div class="flex-1 h-px bg-neutral-200"/>
    <span v-if="$slots.default" class="px-3 text-[11px] text-neutral-400 uppercase tracking-wider"><slot/></span>
    <div v-if="$slots.default" class="flex-1 h-px bg-neutral-200"/>
  </div>
</template>

<script setup lang="ts">
defineProps<{ vertical?: boolean }>()
</script>
