<script setup lang="ts">
import MarketingNav from './components/MarketingNav.vue'
import Footer from './components/Footer.vue'
</script>

<template>
  <div class="min-h-screen flex flex-col bg-white">
    <MarketingNav />
    <main class="flex-1">
      <router-view v-slot="{ Component }">
        <component :is="Component" />
      </router-view>
    </main>
    <Footer />
  </div>
</template>
