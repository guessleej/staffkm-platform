<template>
  <div class="relative inline-block" v-click-outside="close">
    <span @click="toggle"><slot name="trigger"/></span>
    <transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0 scale-95 -translate-y-1"
      leave-active-class="transition duration-100 ease-in"
      leave-to-class="opacity-0 scale-95 -translate-y-1"
    >
      <div v-if="open"
           :class="['absolute z-40 mt-1.5 min-w-[160px] py-1 rounded-xl border border-neutral-200 bg-surface-raised shadow-lg',
                    align === 'right' ? 'right-0' : 'left-0']"
           role="menu">
        <slot name="menu" :close="close"/>
        <template v-if="items">
          <button v-for="(it, i) in items" :key="i"
                  @click="onSelect(it)"
                  :disabled="it.disabled"
                  :class="['w-full text-left px-3 py-2 text-sm transition-colors flex items-center gap-2',
                           it.danger ? 'text-danger-600 hover:bg-danger-50' : 'text-fg hover:bg-neutral-50',
                           it.disabled ? 'opacity-40 cursor-not-allowed' : '']">
            <span v-if="it.icon" class="text-base flex-shrink-0">{{ it.icon }}</span>
            <span class="flex-1">{{ it.label }}</span>
            <span v-if="it.shortcut" class="text-[10px] text-neutral-400 font-mono">{{ it.shortcut }}</span>
          </button>
        </template>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

export interface DropdownItem {
  label:    string
  icon?:    string
  shortcut?: string
  danger?:  boolean
  disabled?: boolean
  onClick?: () => void | Promise<void>
}
defineProps<{
  items?: DropdownItem[]
  align?: 'left' | 'right'
}>()

const open = ref(false)
function toggle() { open.value = !open.value }
function close() { open.value = false }
async function onSelect(it: DropdownItem) {
  if (it.disabled) return
  await it.onClick?.()
  close()
}

// click-outside directive（內建簡化版；避免依賴 @vueuse）
const vClickOutside = {
  mounted(el: HTMLElement, binding: any) {
    el.__co__ = (e: MouseEvent) => {
      if (!el.contains(e.target as Node)) binding.value()
    }
    document.addEventListener('click', el.__co__)
  },
  unmounted(el: HTMLElement) {
    document.removeEventListener('click', el.__co__)
    delete el.__co__
  },
}
</script>
