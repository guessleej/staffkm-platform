<template>
  <div class="flex flex-col h-full">
    <div class="h-14 border-b border-gray-200 px-6 flex items-center bg-white">
      <h2 class="font-semibold text-gray-800">{{ title }}</h2>
    </div>
    <div class="flex-1 flex items-center justify-center text-gray-400">
      <p>此頁面開發中…</p>
    </div>
  </div>
</template>
<script setup lang="ts">
import { useRoute } from 'vue-router'
const route = useRoute()
const title = String(route.meta.title || '頁面')
</script>
