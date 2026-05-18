<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { CaseStudy } from '../data/cases'

defineProps<{ caseItem: CaseStudy }>()
</script>

<template>
  <RouterLink
    :to="`/cases/${caseItem.slug}`"
    class="block p-6 rounded-xl border border-ink-100 bg-white hover:border-brand-500 hover:shadow-md transition group"
  >
    <div class="text-xs text-brand-600 font-medium mb-2">{{ caseItem.industry }}</div>
    <h3 class="font-semibold text-xl mb-3 text-ink-900 group-hover:text-brand-700">
      {{ caseItem.headline }}
    </h3>
    <p class="text-ink-500 text-sm leading-relaxed mb-5">{{ caseItem.summary }}</p>

    <div class="flex flex-wrap gap-4 pt-4 border-t border-ink-100">
      <div
        v-for="m in caseItem.metrics.slice(0, 2)"
        :key="m.label"
        class="flex-1 min-w-[100px]"
      >
        <div class="text-2xl font-bold text-brand-600">{{ m.value }}</div>
        <div class="text-xs text-ink-500 mt-1">{{ m.label }}</div>
      </div>
    </div>

    <div class="mt-5 text-sm text-brand-600 font-medium">看完整案例 →</div>
  </RouterLink>
</template>
