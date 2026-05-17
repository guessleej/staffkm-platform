<template>
  <section class="px-3 mb-3">
    <h4 v-if="title" class="px-2 mb-1 text-[10px] font-bold uppercase tracking-wider text-neutral-400">
      {{ title }}
    </h4>
    <div class="space-y-0.5"><slot/></div>
  </section>
</template>

<script setup lang="ts">
defineProps<{ title?: string }>()
</script>
