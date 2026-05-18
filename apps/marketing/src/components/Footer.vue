<script setup lang="ts">
import { RouterLink } from 'vue-router'
const year = new Date().getFullYear()
</script>

<template>
  <footer class="border-t border-ink-100 bg-ink-100/40 mt-20">
    <div class="container-content py-12 grid md:grid-cols-4 gap-8 text-sm">
      <div>
        <div class="flex items-center gap-2 font-bold text-base mb-3">
          <span class="w-7 h-7 rounded-md bg-brand-600 text-white grid place-items-center">S</span>
          staffKM
        </div>
        <p class="text-ink-500 leading-relaxed">
          企業 AI 知識管理平台 — 把公司知識變成員工的 AI 助理。
        </p>
      </div>

      <div>
        <h4 class="font-semibold mb-3">產品</h4>
        <ul class="space-y-2 text-ink-500">
          <li><RouterLink to="/" class="hover:text-brand-600">功能介紹</RouterLink></li>
          <li><RouterLink to="/pricing" class="hover:text-brand-600">價格方案</RouterLink></li>
          <li><a href="https://docs.staffkm.dev" class="hover:text-brand-600">產品文件</a></li>
          <li><a href="/signup" class="hover:text-brand-600">免費試用</a></li>
        </ul>
      </div>

      <div>
        <h4 class="font-semibold mb-3">公司</h4>
        <ul class="space-y-2 text-ink-500">
          <li><RouterLink to="/about" class="hover:text-brand-600">關於我們</RouterLink></li>
          <li><RouterLink to="/cases" class="hover:text-brand-600">客戶案例</RouterLink></li>
          <li><a href="mailto:hi@staffkm.dev" class="hover:text-brand-600">聯絡我們</a></li>
          <li><a href="mailto:sales@staffkm.dev" class="hover:text-brand-600">企業洽詢</a></li>
        </ul>
      </div>

      <div>
        <h4 class="font-semibold mb-3">資源</h4>
        <ul class="space-y-2 text-ink-500">
          <li><a href="https://github.com/guessleej/staffkm-platform" class="hover:text-brand-600">GitHub</a></li>
          <li><a href="https://docs.staffkm.dev/changelog" class="hover:text-brand-600">Changelog</a></li>
          <li><a href="mailto:security@staffkm.dev" class="hover:text-brand-600">安全揭露</a></li>
        </ul>
      </div>
    </div>

    <div class="border-t border-ink-100">
      <div class="container-content py-5 flex flex-col md:flex-row items-center justify-between gap-3 text-xs text-ink-500">
        <p>© {{ year }} staffKM. Apache-2.0 License.</p>
        <div class="flex gap-4">
          <a href="#" class="hover:text-brand-600" aria-label="GitHub">GitHub</a>
          <a href="#" class="hover:text-brand-600" aria-label="LinkedIn">LinkedIn</a>
          <a href="#" class="hover:text-brand-600" aria-label="X">X</a>
        </div>
      </div>
    </div>
  </footer>
</template>
