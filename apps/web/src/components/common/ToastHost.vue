<template>
  <Teleport to="body">
    <div
      class="fixed bottom-4 right-4 z-[200] flex flex-col gap-2 pointer-events-none"
      aria-live="polite"
      aria-atomic="false"
      role="status"
    >
      <transition-group
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="opacity-0 translate-y-2"
        leave-active-class="transition duration-150 ease-in"
        leave-to-class="opacity-0 translate-y-2"
      >
        <div
          v-for="t in toast._queue.value"
          :key="t.id"
          class="pointer-events-auto min-w-[240px] max-w-md px-4 py-2.5 rounded-xl shadow-lg border flex items-start gap-2 text-sm bg-surface-raised"
          :class="toneClass(t.kind)"
          role="alert"
        >
          <span class="text-base flex-shrink-0 mt-0.5" aria-hidden="true">{{ icon(t.kind) }}</span>
          <span class="flex-1 leading-snug text-neutral-800">{{ t.message }}</span>
          <button
            @click="toast.dismiss(t.id)"
            class="ml-1 text-neutral-300 hover:text-neutral-600 transition"
            :aria-label="`關閉通知：${t.message}`"
          >×</button>
        </div>
      </transition-group>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useToast, type ToastKind } from '../../composables/useToast'

const toast = useToast()

function toneClass(k: ToastKind) {
  return {
    success: 'border-success-200',
    error:   'border-danger-200',
    info:    'border-neutral-200',
    warning: 'border-warning-200',
  }[k] || 'border-neutral-200'
}

function icon(k: ToastKind) {
  return { success: '✓', error: '✕', info: 'ⓘ', warning: '!' }[k] || 'ⓘ'
}
</script>
