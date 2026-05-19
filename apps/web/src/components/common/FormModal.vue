<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  modelValue: boolean
  title: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
  closeOnBackdrop?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  size: 'md',
  closeOnBackdrop: true,
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'close'): void
}>()

const sizeClass = computed(() => {
  switch (props.size) {
    case 'sm': return 'max-w-md'
    case 'lg': return 'max-w-2xl'
    case 'xl': return 'max-w-3xl'
    case 'md':
    default:   return 'max-w-lg'
  }
})

function close() {
  emit('update:modelValue', false)
  emit('close')
}

function onBackdrop() {
  if (props.closeOnBackdrop) close()
}
</script>

<template>
  <Teleport to="body">
    <transition name="modal">
      <div
        v-if="modelValue"
        class="fixed inset-0 z-50 flex items-center justify-center
               bg-neutral-900/40 backdrop-blur-sm p-4"
        @click.self="onBackdrop"
      >
        <div
          class="card-warm w-full flex flex-col overflow-hidden animate-modal-pop"
          :class="[sizeClass, 'max-h-[90vh]']"
        >
          <header class="flex items-center justify-between px-6 py-4 border-b border-bd">
            <h3 class="heading-section">{{ title }}</h3>
            <button
              type="button"
              class="w-8 h-8 flex items-center justify-center rounded-lg
                     text-fg-secondary hover:bg-neutral-100 hover:text-fg
                     transition-colors"
              aria-label="關閉"
              @click="close"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
                   stroke="currentColor" stroke-width="2" stroke-linecap="round"
                   stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </header>
          <main class="flex-1 overflow-y-auto p-6 space-y-5">
            <slot />
          </main>
          <footer
            v-if="$slots.footer"
            class="flex items-center justify-end gap-2 px-6 py-4 border-t border-bd bg-neutral-50/50"
          >
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </transition>
  </Teleport>
</template>
