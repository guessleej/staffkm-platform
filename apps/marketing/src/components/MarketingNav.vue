<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'

const open = ref(false)
function close() {
  open.value = false
}
</script>

<template>
  <header class="sticky top-0 z-40 bg-white/90 backdrop-blur border-b border-ink-100">
    <div class="container-content flex items-center justify-between h-16">
      <RouterLink to="/" class="flex items-center gap-2 font-bold text-lg" @click="close">
        <span
          class="w-8 h-8 rounded-lg bg-brand-600 text-white grid place-items-center font-bold"
        >S</span>
        <span>staffKM</span>
      </RouterLink>

      <nav class="hidden md:flex items-center gap-7 text-sm text-ink-700">
        <RouterLink to="/" class="hover:text-brand-600" exact-active-class="text-brand-600">首頁</RouterLink>
        <RouterLink to="/pricing" class="hover:text-brand-600" active-class="text-brand-600">價格</RouterLink>
        <RouterLink to="/cases" class="hover:text-brand-600" active-class="text-brand-600">案例</RouterLink>
        <RouterLink to="/about" class="hover:text-brand-600" active-class="text-brand-600">關於</RouterLink>
        <a href="https://docs.staffkm.dev" class="hover:text-brand-600">文件</a>
      </nav>

      <div class="hidden md:flex items-center gap-3">
        <a href="/login" class="btn btn-ghost">登入</a>
        <a href="/signup" class="btn btn-primary">免費試用</a>
      </div>

      <button
        class="md:hidden p-2 -mr-2 text-ink-700"
        aria-label="menu"
        @click="open = !open"
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>
    </div>

    <div v-if="open" class="md:hidden border-t border-ink-100 bg-white">
      <div class="container-content py-4 flex flex-col gap-3 text-ink-700">
        <RouterLink to="/" @click="close">首頁</RouterLink>
        <RouterLink to="/pricing" @click="close">價格</RouterLink>
        <RouterLink to="/cases" @click="close">案例</RouterLink>
        <RouterLink to="/about" @click="close">關於</RouterLink>
        <a href="https://docs.staffkm.dev">文件</a>
        <div class="flex gap-3 pt-3 border-t border-ink-100">
          <a href="/login" class="btn btn-outline flex-1">登入</a>
          <a href="/signup" class="btn btn-primary flex-1">免費試用</a>
        </div>
      </div>
    </div>
  </header>
</template>
