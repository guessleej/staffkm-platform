<template>
  <Teleport to="body">
    <transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0"
      leave-active-class="transition duration-100 ease-in"
      leave-to-class="opacity-0"
    >
      <div
        v-if="current"
        class="fixed inset-0 z-[300] flex items-center justify-center p-4 bg-black/40"
        @click.self="onCancel"
        @keydown.esc="onCancel"
      >
        <div
          ref="panelRef"
          tabindex="-1"
          class="w-full max-w-md bg-surface-raised rounded-2xl shadow-2xl overflow-hidden focus:outline-none"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="`dialog-title-${current.id}`"
          :aria-describedby="`dialog-msg-${current.id}`"
        >
          <div class="px-5 pt-5 pb-3">
            <h3 :id="`dialog-title-${current.id}`" class="text-sm font-semibold text-neutral-900">
              {{ current.title || (current.kind === 'confirm' ? '請確認' : '提示') }}
            </h3>
            <p :id="`dialog-msg-${current.id}`" class="mt-2 text-sm text-neutral-700 whitespace-pre-wrap leading-relaxed">
              {{ current.message }}
            </p>
          </div>
          <div class="px-5 py-3 bg-neutral-50 border-t border-neutral-100 flex justify-end gap-2">
            <button
              v-if="current.kind === 'confirm'"
              @click="onCancel"
              class="h-9 px-4 text-sm rounded-lg border border-neutral-200 text-neutral-700 hover:bg-neutral-100 transition"
            >{{ current.cancelLabel }}</button>
            <button
              ref="okRef"
              @click="onConfirm"
              :class="okClass"
              class="h-9 px-4 text-sm rounded-lg text-white transition"
            >{{ current.confirmLabel }}</button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useDialog, resolveDialog } from '../../composables/useDialog'

const dialog = useDialog()
const current = computed(() => dialog._queue.value[0] || null)

const panelRef = ref<HTMLElement | null>(null)
const okRef    = ref<HTMLButtonElement | null>(null)

const okClass = computed(() => {
  const tone = current.value?.tone ?? 'default'
  return {
    default: 'bg-brand-600 hover:bg-brand-700',
    danger:  'bg-danger-600 hover:bg-danger-700',
    success: 'bg-success-600 hover:bg-success-700',
  }[tone]
})

watch(current, async (c) => {
  if (!c) return
  await nextTick()
  okRef.value?.focus()
})

function onConfirm() {
  if (current.value) resolveDialog(current.value.id, true)
}
function onCancel() {
  if (!current.value) return
  // alert 也視為「確認」（沒有取消可選）
  resolveDialog(current.value.id, current.value.kind === 'alert')
}
</script>
