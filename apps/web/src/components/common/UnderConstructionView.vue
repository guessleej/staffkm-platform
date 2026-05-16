<template>
  <div class="flex flex-col h-full bg-surface-base">
    <!-- 頁首 -->
    <div class="h-14 border-b border-neutral-200 bg-surface-raised px-6 flex items-center flex-shrink-0">
      <h2 class="font-semibold text-neutral-900">{{ title }}</h2>
    </div>

    <!-- 內容 -->
    <div class="flex-1 overflow-y-auto">
      <div class="max-w-2xl mx-auto px-6 py-16">
        <!-- 標籤 chip -->
        <div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-warning-50 text-warning-700 text-[11px] font-semibold mb-4">
          <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          {{ statusLabel }}
        </div>

        <h1 class="text-2xl font-semibold text-neutral-900 mb-2">{{ title }}</h1>
        <p class="text-sm text-neutral-600 leading-relaxed mb-8">
          {{ description }}
        </p>

        <!-- 預計能力清單 -->
        <div
          v-if="features?.length"
          class="bg-surface-raised border border-neutral-200 rounded-xl p-5 mb-6"
        >
          <p class="text-xs uppercase tracking-widest text-neutral-500 mb-3">預計能力</p>
          <ul class="space-y-2">
            <li v-for="(f, i) in features" :key="i" class="flex items-start gap-2 text-sm text-neutral-700">
              <svg class="w-4 h-4 mt-0.5 flex-shrink-0 text-neutral-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="9" />
              </svg>
              <span>{{ f }}</span>
            </li>
          </ul>
        </div>

        <!-- 自訂 slot 區塊（給呼叫端塞「立刻試試」CTA 或臨時表單）-->
        <div v-if="$slots.default" class="mb-6"><slot /></div>

        <!-- 返回首頁 -->
        <router-link
          to="/chat"
          class="inline-flex items-center gap-1.5 h-9 px-4 text-sm font-medium text-neutral-700 bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50 transition"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
          </svg>
          回到對話
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    title:       string
    description: string
    features?:   string[]
    statusLabel?: string
  }>(),
  { statusLabel: '準備中' },
)
</script>
