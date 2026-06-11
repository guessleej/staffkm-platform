<template>
  <!-- v5.13: Teleport 到 body —— 否則祖先（page-fade-wrap 動畫）的 transform 會成為
       fixed 的 containing block，把這條 bottom-6 工具列定位到捲動內容底部、跑出畫面外
       （batch 全選了卻看不到刪除列即此雷）。掛到 body 下 → fixed 永遠以視窗為基準。 -->
  <Teleport to="body">
  <transition
    enter-active-class="transition duration-150 ease-out"
    enter-from-class="opacity-0 translate-y-2"
    leave-active-class="transition duration-100 ease-in"
    leave-to-class="opacity-0 translate-y-2"
  >
    <div
      v-if="n > 0"
      class="fixed bottom-6 left-1/2 -translate-x-1/2 z-40
             flex items-center gap-2
             pl-4 pr-2 py-2 rounded-2xl
             bg-neutral-900 text-white shadow-lg"
    >
      <span class="text-sm font-medium">
        {{ $t('batch.selectedCount', { n }) }}
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
  </Teleport>
</template>

<script setup lang="ts">
import { computed, unref } from 'vue'
// v5.13 雷修：呼叫端常寫 :count="batch.count"，但 batch 是「plain object」、batch.count 是
// ComputedRef，作為巢狀屬性傳進 prop 時 Vue 不自動解包 → 子端收到 ref 物件、count>0 永遠
// false → 工具列從來沒顯示過（文件/知識庫/應用三處全中）。用 unref 同時吃 ref 或數字。
const props = defineProps<{ count: number }>()
defineEmits<{ (e: 'clear'): void }>()
const n = computed(() => Number(unref(props.count as unknown)) || 0)
</script>
