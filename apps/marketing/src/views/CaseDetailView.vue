<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { findCase } from '../data/cases'

const route = useRoute()
const caseItem = computed(() => findCase(route.params.slug as string))
</script>

<template>
  <section class="section">
    <div class="container-content max-w-4xl">
      <RouterLink to="/cases" class="text-sm text-brand-600 hover:underline">← 回案例列表</RouterLink>

      <template v-if="caseItem">
        <div class="mt-6">
          <div class="text-sm text-brand-600 font-medium mb-2">{{ caseItem.industry }} · {{ caseItem.company }}</div>
          <h1 class="text-3xl md:text-5xl font-bold mb-4 leading-tight">{{ caseItem.headline }}</h1>
          <p class="text-lg text-ink-500 leading-relaxed">{{ caseItem.summary }}</p>
        </div>

        <!-- Metrics -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 my-12 p-6 bg-brand-50 rounded-xl border border-brand-100">
          <div v-for="m in caseItem.metrics" :key="m.label" class="text-center">
            <div class="text-3xl font-bold text-brand-700">{{ m.value }}</div>
            <div class="text-xs text-ink-500 mt-1">{{ m.label }}</div>
          </div>
        </div>

        <!-- Content sections -->
        <div class="space-y-10 mt-12">
          <div>
            <h2 class="text-xl font-bold mb-3">挑戰</h2>
            <p class="text-ink-700 leading-relaxed">{{ caseItem.challenge }}</p>
          </div>
          <div>
            <h2 class="text-xl font-bold mb-3">解決方案</h2>
            <p class="text-ink-700 leading-relaxed">{{ caseItem.solution }}</p>
          </div>
          <div>
            <h2 class="text-xl font-bold mb-3">成果</h2>
            <p class="text-ink-700 leading-relaxed">{{ caseItem.result }}</p>
          </div>
        </div>

        <!-- Quote -->
        <blockquote class="my-12 p-8 rounded-xl bg-ink-100/50 border-l-4 border-brand-600">
          <p class="text-lg text-ink-900 italic leading-relaxed">"{{ caseItem.quote.text }}"</p>
          <footer class="mt-4 text-sm text-ink-500">
            — <strong class="text-ink-700">{{ caseItem.quote.author }}</strong>, {{ caseItem.quote.title }}
          </footer>
        </blockquote>

        <!-- CTA -->
        <div class="text-center mt-16 p-8 rounded-xl bg-gradient-to-br from-brand-600 to-brand-900 text-white">
          <h3 class="text-2xl font-bold mb-3">想看看你的團隊適不適合？</h3>
          <p class="text-brand-100 mb-6">14 天免費試用，不需信用卡。</p>
          <a href="/signup" class="btn btn-lg bg-white text-brand-700 hover:bg-brand-50">免費試用</a>
        </div>
      </template>

      <template v-else>
        <div class="mt-12 text-center text-ink-500">
          <p>找不到此案例。</p>
        </div>
      </template>
    </div>
  </section>
</template>
