<script setup lang="ts">
defineProps<{
  icon: string
  title: string
  description: string
}>()
</script>

<template>
  <article class="p-6 rounded-xl border border-ink-100 bg-white hover:border-brand-500 hover:shadow-sm transition">
    <div class="text-3xl mb-4">{{ icon }}</div>
    <h3 class="font-semibold text-lg mb-2 text-ink-900">{{ title }}</h3>
    <p class="text-ink-500 leading-relaxed text-sm">{{ description }}</p>
  </article>
</template>
