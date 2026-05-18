<script setup lang="ts">
import HeroSection from '../components/HeroSection.vue'
import FeatureCard from '../components/FeatureCard.vue'
import { features } from '../data/features'

const steps = [
  {
    n: '1',
    title: '上傳知識',
    desc: '把 PDF / Word / 內部 wiki / 網頁匯入。系統自動 chunk、embedding、建索引。',
  },
  {
    n: '2',
    title: '設計 Application',
    desc: '拖拉 30+ workflow 節點：RAG 檢索 → LLM 生成 → 條件分流 → 回呼 Webhook。',
  },
  {
    n: '3',
    title: '上線給員工用',
    desc: '串 Slack / Teams / LINE / Web embed。員工提問直接得到含 citation 的答案。',
  },
]

const logos = ['Acme Tech', 'Northwind', 'Globex', 'Initech', 'Umbrella', 'Pied Piper']
</script>

<template>
  <HeroSection />

  <!-- Features -->
  <section class="section">
    <div class="container-content">
      <h2 class="h-section text-center">行政人員需要的能力，一次到位</h2>
      <p class="h-section-sub mx-auto text-center">
        對標 MaxKB 功能完整度、走 claude.ai 視覺風。從知識管理到 workflow 自動化，不需要組合 5 個 SaaS。
      </p>
      <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
        <FeatureCard
          v-for="f in features"
          :key="f.title"
          :icon="f.icon"
          :title="f.title"
          :description="f.description"
        />
      </div>
    </div>
  </section>

  <!-- How it works -->
  <section class="section bg-ink-100/40">
    <div class="container-content">
      <h2 class="h-section text-center">3 步驟上線</h2>
      <p class="h-section-sub mx-auto text-center">不需要顧問、不需要外部團隊。下午部署、隔天員工就能用。</p>

      <div class="grid md:grid-cols-3 gap-6">
        <div
          v-for="s in steps"
          :key="s.n"
          class="bg-white p-8 rounded-xl border border-ink-100"
        >
          <div
            class="w-12 h-12 rounded-full bg-brand-600 text-white grid place-items-center font-bold text-lg mb-5"
          >{{ s.n }}</div>
          <h3 class="font-semibold text-lg mb-2">{{ s.title }}</h3>
          <p class="text-ink-500 text-sm leading-relaxed">{{ s.desc }}</p>
        </div>
      </div>
    </div>
  </section>

  <!-- Customer logos -->
  <section class="section">
    <div class="container-content text-center">
      <p class="text-sm text-ink-500 mb-8">已被以下類型企業採用</p>
      <div class="grid grid-cols-2 md:grid-cols-6 gap-6 opacity-60">
        <div
          v-for="l in logos"
          :key="l"
          class="h-12 rounded-md bg-ink-100 grid place-items-center text-ink-500 text-sm font-medium"
        >{{ l }}</div>
      </div>
    </div>
  </section>

  <!-- CTA -->
  <section class="section">
    <div class="container-content">
      <div class="rounded-2xl bg-gradient-to-br from-brand-600 to-brand-900 text-white p-12 md:p-16 text-center">
        <h2 class="text-3xl md:text-4xl font-bold mb-4">準備好把知識變成戰力？</h2>
        <p class="text-brand-100 text-lg mb-8 max-w-xl mx-auto">
          14 天免費試用，完整功能，不需信用卡。
        </p>
        <div class="flex flex-col sm:flex-row gap-3 justify-center">
          <a href="/signup" class="btn btn-lg bg-white text-brand-700 hover:bg-brand-50">
            免費試用 14 天
          </a>
          <a href="mailto:sales@staffkm.dev" class="btn btn-lg border border-white/40 text-white hover:bg-white/10">
            聯絡業務
          </a>
        </div>
      </div>
    </div>
  </section>
</template>
