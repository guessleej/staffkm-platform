<template>
  <transition
    enter-active-class="transition duration-150 ease-out"
    enter-from-class="opacity-0 translate-y-2"
    leave-active-class="transition duration-100 ease-in"
    leave-to-class="opacity-0 translate-y-2"
  >
    <div
      v-if="count > 0"
      class="fixed bottom-6 left-1/2 -translate-x-1/2 z-40
             flex items-center gap-2
             pl-4 pr-2 py-2 rounded-2xl
             bg-neutral-900 text-white shadow-lg"
    >
      <span class="text-sm font-medium">
        {{ $t('batch.selectedCount', { n: count }) }}
      </span>

      <!-- 分隔線 -->
      <span class="w-px h-5 bg-white/20 mx-1"></span>

      <!-- 操作按鈕 slot —— 由呼叫端注入「移至 / 刪除 / 匯出」等 -->
      <slot />

      <!-- 結尾固定：取消選取 -->
      <button
        @click="$emit('clear')"
        class="ml-1 w-8 h-8 flex items-center justify-center rounded-lg text-white/70 hover:bg-white/10 hover:text-white transition"
        :title="$t('batch.clear')"
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
        </svg>
      </button>
    </div>
  </transition>
</template>

<script setup lang="ts">
defineProps<{ count: number }>()
defineEmits<{ (e: 'clear'): void }>()
</script>
