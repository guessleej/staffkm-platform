<template>
  <router-view />

  <!-- UX 對齊輪 #1：全域 toast / dialog 容器 -->
  <ToastHost />
  <DialogHost />
  <!-- 設計系統 v1.1：⌘K command palette -->
  <CommandPalette />

  <!--
    Cold-start 指示：用右下角小 toast 取代全螢幕 overlay
    避免使用者把「dim + blur 效果」誤判為「畫面空白」。
    + 300ms 延遲：短任務不閃，避免每次切頁面都浮現一下。
  -->
  <transition
    enter-active-class="transition duration-200 ease-out"
    enter-from-class="opacity-0 translate-y-2"
    leave-active-class="transition duration-150 ease-in"
    leave-to-class="opacity-0 translate-y-2"
  >
    <div
      v-if="showColdStart"
      class="fixed bottom-4 right-4 z-[100]
             bg-surface-raised border border-neutral-200 rounded-xl shadow-lg
             px-4 py-2.5 flex items-center gap-2.5 pointer-events-none"
    >
      <svg class="animate-spin w-4 h-4 text-brand-600 flex-shrink-0" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
      </svg>
      <p class="text-xs text-neutral-700">載入中…</p>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useAuthStore } from './stores/auth'
import { useWorkspaceStore } from './stores/workspace'
import ToastHost from './components/common/ToastHost.vue'
import DialogHost from './components/common/DialogHost.vue'
import CommandPalette from './components/common/CommandPalette.vue'

const auth = useAuthStore()
const workspace = useWorkspaceStore()

// 真正進入 loading 狀態
const isLoading = computed(() => {
  return (
    (!!auth.accessToken && !auth.user) ||
    workspace.loading
  )
})

// 加 300ms debounce：短任務（< 300ms）不顯示 toast，避免閃爍
const showColdStart = ref(false)
let _showTimer: ReturnType<typeof setTimeout> | null = null

watch(isLoading, (loading) => {
  if (_showTimer) { clearTimeout(_showTimer); _showTimer = null }
  if (loading) {
    _showTimer = setTimeout(() => { showColdStart.value = true }, 300)
  } else {
    showColdStart.value = false
  }
}, { immediate: true })

onMounted(() => auth.init())
</script>
