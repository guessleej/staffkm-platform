<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-base ease-out"
      enter-from-class="opacity-0"
      leave-active-class="transition duration-fast ease-in"
      leave-to-class="opacity-0"
    >
      <div v-if="modelValue" class="fixed inset-0 z-modal flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm" @click.self="closable && close()">
        <Transition
          enter-active-class="transition duration-base ease-out"
          enter-from-class="opacity-0 translate-y-4 scale-95"
          leave-active-class="transition duration-fast ease-in"
          leave-to-class="opacity-0 scale-95"
          appear
        >
          <div v-if="modelValue" :class="panelClasses">
            <div v-if="title || $slots.header" class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between">
              <h2 class="text-base font-semibold text-neutral-900">
                <slot name="header">{{ title }}</slot>
              </h2>
              <button v-if="closable" type="button" class="p-1 rounded-md text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 transition" @click="close">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>
            <div class="px-5 py-4 max-h-[70vh] overflow-y-auto"><slot /></div>
            <div v-if="$slots.footer" class="px-5 py-3 border-t border-neutral-100 flex items-center justify-end gap-2 bg-neutral-50">
              <slot name="footer" />
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, watch, onUnmounted } from 'vue'

const props = withDefaults(defineProps<{
  modelValue: boolean
  title?:    string
  size?:     'sm' | 'md' | 'lg' | 'xl' | 'full'
  closable?: boolean
}>(), { size: 'md', closable: true })

const emit = defineEmits<{ 'update:modelValue': [v: boolean]; close: [] }>()

const sizeMap: Record<string, string> = {
  sm:   'max-w-sm',
  md:   'max-w-lg',
  lg:   'max-w-2xl',
  xl:   'max-w-4xl',
  full: 'max-w-[95vw]',
}
const panelClasses = computed(() => [
  'w-full bg-surface-raised rounded-2xl shadow-2xl overflow-hidden',
  sizeMap[props.size],
])

function close() {
  emit('update:modelValue', false)
  emit('close')
}

// ESC 關閉
function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.closable && props.modelValue) close()
}
watch(() => props.modelValue, (open) => {
  if (open) {
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
  } else {
    document.removeEventListener('keydown', onKey)
    document.body.style.overflow = ''
  }
})
onUnmounted(() => {
  document.removeEventListener('keydown', onKey)
  document.body.style.overflow = ''
})
</script>
