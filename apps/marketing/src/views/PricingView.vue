<script setup lang="ts">
import { plans, faqs } from '../data/pricing'
import PricingTable from '../components/PricingTable.vue'
</script>

<template>
  <section class="section">
    <div class="container-content">
      <div class="text-center mb-16">
        <h1 class="text-4xl md:text-5xl font-bold mb-4">簡單透明的價格</h1>
        <p class="text-lg text-ink-500 max-w-xl mx-auto">
          從 14 天免費試用開始，按團隊規模升級。Enterprise 提供 on-prem 部署與 SLA。
        </p>
      </div>

      <div class="grid md:grid-cols-2 lg:grid-cols-4 gap-5">
        <div
          v-for="plan in plans"
          :key="plan.id"
          class="relative rounded-xl border bg-white p-6 flex flex-col"
          :class="plan.highlight
            ? 'border-brand-600 shadow-lg ring-1 ring-brand-600'
            : 'border-ink-100'"
        >
          <div
            v-if="plan.badge"
            class="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-brand-600 text-white text-xs font-semibold"
          >{{ plan.badge }}</div>

          <h3 class="font-semibold text-xl mb-2">{{ plan.name }}</h3>
          <div class="mb-1">
            <span class="text-3xl font-bold">{{ plan.price }}</span>
          </div>
          <p class="text-sm text-ink-500 mb-6">{{ plan.priceNote }}</p>

          <ul class="space-y-2.5 mb-8 flex-1">
            <li
              v-for="f in plan.features"
              :key="f"
              class="flex items-start gap-2 text-sm text-ink-700"
            >
              <span class="text-brand-600 font-bold mt-0.5">✓</span>
              <span>{{ f }}</span>
            </li>
          </ul>

          <a
            :href="plan.ctaHref"
            class="btn w-full"
            :class="plan.highlight ? 'btn-primary' : 'btn-outline'"
          >{{ plan.cta }}</a>
        </div>
      </div>
    </div>
  </section>

  <!-- Comparison -->
  <section class="section bg-ink-100/40">
    <div class="container-content">
      <h2 class="h-section text-center">功能完整對比</h2>
      <p class="h-section-sub text-center mx-auto">看一眼決定哪個 plan 適合你的團隊。</p>
      <div class="bg-white rounded-xl border border-ink-100 p-6">
        <PricingTable />
      </div>
    </div>
  </section>

  <!-- FAQ -->
  <section class="section">
    <div class="container-content max-w-3xl">
      <h2 class="h-section text-center">常見問題</h2>
      <div class="space-y-4 mt-12">
        <details
          v-for="f in faqs"
          :key="f.q"
          class="group rounded-lg border border-ink-100 bg-white p-5"
        >
          <summary class="cursor-pointer font-medium text-ink-900 list-none flex justify-between items-center">
            <span>{{ f.q }}</span>
            <span class="text-brand-600 group-open:rotate-45 transition-transform text-2xl leading-none">+</span>
          </summary>
          <p class="mt-3 text-ink-500 text-sm leading-relaxed">{{ f.a }}</p>
        </details>
      </div>
    </div>
  </section>
</template>
