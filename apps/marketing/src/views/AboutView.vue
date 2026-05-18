<script setup lang="ts">
const values = [
  { icon: '🏠', title: '資料不出園區', desc: '地端 LLM 預設、Ollama 開箱即用。Enterprise 客戶整套 on-prem 部署。' },
  { icon: '🔓', title: '不被 vendor 鎖', desc: 'Apache-2.0 license、25+ provider 抽象介面。換 model、換廠商不痛。' },
  { icon: '🛠', title: 'Production-ready', desc: '14 份 RFC、105+ PR、完整 backup / DR runbook、Helm chart。' },
  { icon: '🌏', title: '中文優先', desc: 'bge-m3 中文 embedding、繁體中文 UI、台灣 / 香港產業情境設計。' },
]
</script>

<template>
  <section class="section">
    <div class="container-content max-w-4xl">
      <div class="text-center mb-16">
        <h1 class="text-4xl md:text-5xl font-bold mb-4">關於 staffKM</h1>
        <p class="text-lg text-ink-500 leading-relaxed">
          我們相信：企業 AI 不該是黑盒、不該綁雲端、不該需要顧問教半年。<br />
          staffKM 把「企業知識管理」做到開箱可用、地端可控、價格透明。
        </p>
      </div>

      <!-- Mission -->
      <div class="bg-gradient-to-br from-brand-50 to-white rounded-xl border border-brand-100 p-10 mb-16">
        <h2 class="text-2xl font-bold mb-4">我們的使命</h2>
        <p class="text-ink-700 leading-relaxed">
          讓每個組織都能在自己控制的環境下，把累積的知識變成員工的 AI 助理。
          不必依賴雲端、不必為「資料外洩」焦慮、不必為了一個功能買 5 個 SaaS。
        </p>
      </div>

      <!-- Values -->
      <h2 class="text-2xl font-bold mb-8 text-center">我們的原則</h2>
      <div class="grid md:grid-cols-2 gap-5 mb-16">
        <div
          v-for="v in values"
          :key="v.title"
          class="p-6 rounded-xl border border-ink-100 bg-white"
        >
          <div class="text-3xl mb-3">{{ v.icon }}</div>
          <h3 class="font-semibold text-lg mb-2">{{ v.title }}</h3>
          <p class="text-ink-500 text-sm leading-relaxed">{{ v.desc }}</p>
        </div>
      </div>

      <!-- Contact -->
      <div class="bg-ink-100/50 rounded-xl p-10 text-center">
        <h2 class="text-2xl font-bold mb-4">聯絡我們</h2>
        <p class="text-ink-500 mb-6">不論是業務洽詢、技術支援、安全揭露，都歡迎來信。</p>
        <div class="flex flex-col sm:flex-row gap-3 justify-center">
          <a href="mailto:hi@staffkm.dev" class="btn btn-outline">hi@staffkm.dev</a>
          <a href="mailto:sales@staffkm.dev" class="btn btn-primary">sales@staffkm.dev</a>
        </div>
      </div>
    </div>
  </section>
</template>
