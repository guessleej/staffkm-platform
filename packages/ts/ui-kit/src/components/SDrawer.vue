<template>
  <Teleport to="body">
    <transition enter-active-class="transition-opacity duration-150" enter-from-class="opacity-0"
                leave-active-class="transition-opacity duration-100" leave-to-class="opacity-0">
      <div v-if="modelValue" class="fixed inset-0 z-[300] bg-black/40" @click.self="close" @keydown.esc="close">
        <transition :enter-active-class="`transition-transform duration-200 ease-out`"
                    :enter-from-class="enterFromClass" :enter-to-class="enterToClass"
                    :leave-active-class="`transition-transform duration-150 ease-in`"
                    :leave-from-class="leaveFromClass" :leave-to-class="leaveToClass" appear>
          <aside :class="['absolute bg-surface-raised shadow-2xl flex flex-col',
                          side === 'right' ? 'right-0 top-0 bottom-0 border-l border-neutral-200' :
                          side === 'left'  ? 'left-0 top-0 bottom-0 border-r border-neutral-200' :
                          side === 'top'   ? 'top-0 left-0 right-0 border-b border-neutral-200' :
                                              'bottom-0 left-0 right-0 border-t border-neutral-200',
                          side === 'right' || side === 'left' ? widthClass : heightClass]"
                  role="dialog" aria-modal="true">
            <header v-if="$slots.header || title"
                    class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between flex-shrink-0">
              <div class="min-w-0">
                <h3 v-if="title" class="text-sm font-semibold text-fg truncate">{{ title }}</h3>
                <slot name="header"/>
              </div>
              <button @click="close" class="text-neutral-400 hover:text-fg" aria-label="關閉">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </header>
            <div class="flex-1 overflow-y-auto"><slot/></div>
            <footer v-if="$slots.footer"
                    class="px-5 py-3 border-t border-neutral-100 bg-neutral-50 flex justify-end gap-2 flex-shrink-0">
              <slot name="footer"/>
            </footer>
          </aside>
        </transition>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'
const props = withDefaults(defineProps<{
  modelValue: boolean
  title?: string
  side?: 'right' | 'left' | 'top' | 'bottom'
  width?: string   // tailwind 寬度 class（如 'w-96'）
  height?: string  // top/bottom 才用
}>(), { side: 'right', width: 'w-96', height: 'h-72' })
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()
function close() { emit('update:modelValue', false) }
const widthClass = computed(() => props.width)
const heightClass = computed(() => props.height)
const enterFromClass = computed(() =>
  props.side === 'right' ? 'translate-x-full' :
  props.side === 'left'  ? '-translate-x-full' :
  props.side === 'top'   ? '-translate-y-full' : 'translate-y-full')
const enterToClass = computed(() => 'translate-x-0 translate-y-0')
const leaveFromClass = computed(() => 'translate-x-0 translate-y-0')
const leaveToClass = computed(() => enterFromClass.value)
</script>
