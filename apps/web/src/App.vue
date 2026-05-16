<template>
  <router-view />

  <!-- Cold-start overlay：workspace 還在 retry 時顯示，避免使用者誤判畫面卡住 -->
  <transition
    enter-active-class="transition duration-150 ease-out"
    enter-from-class="opacity-0"
    leave-active-class="transition duration-200 ease-in"
    leave-to-class="opacity-0"
  >
    <div
      v-if="showColdStart"
      class="fixed inset-0 z-[100] flex items-center justify-center bg-neutral-900/30 backdrop-blur-sm pointer-events-none"
    >
      <div class="bg-surface-raised rounded-2xl shadow-xl px-6 py-4 flex items-center gap-3">
        <svg class="animate-spin w-5 h-5 text-brand-600" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
        </svg>
        <div>
          <p class="text-sm font-medium text-neutral-900">服務啟動中…</p>
          <p class="text-[11px] text-neutral-500 mt-0.5">後端容器仍在 warm-up，請稍候 5 秒</p>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useAuthStore } from './stores/auth'
import { useWorkspaceStore } from './stores/workspace'

const auth = useAuthStore()
const workspace = useWorkspaceStore()

// 已有 token 但 user 沒回 / workspace 還在 load 中 → 顯示 cold-start overlay
const showColdStart = computed(() => {
  return (
    (!!auth.accessToken && !auth.user) ||
    workspace.loading
  )
})

onMounted(() => auth.init())
</script>
