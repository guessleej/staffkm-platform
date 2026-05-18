<script setup lang="ts">
import { cases } from '../data/cases'
import CaseCard from '../components/CaseCard.vue'
</script>

<template>
  <section class="section">
    <div class="container-content">
      <div class="text-center mb-16">
        <h1 class="text-4xl md:text-5xl font-bold mb-4">客戶怎麼用 staffKM</h1>
        <p class="text-lg text-ink-500 max-w-2xl mx-auto">
          從 500 人科技公司、區域銀行到 300 間門市的零售集團，看真實導入結果與量化效益。
        </p>
      </div>

      <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        <CaseCard v-for="c in cases" :key="c.slug" :case-item="c" />
      </div>

      <div class="text-center mt-16">
        <p class="text-ink-500 mb-4">想看你產業的應用情境？</p>
        <a href="mailto:sales@staffkm.dev" class="btn btn-outline">聯絡業務團隊</a>
      </div>
    </div>
  </section>
</template>
