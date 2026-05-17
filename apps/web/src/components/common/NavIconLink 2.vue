<template>
  <router-link
    :to="to"
    class="group relative inline-flex items-center justify-center w-9 h-9 rounded-lg transition-colors"
    :class="isActive
      ? 'bg-brand-50 text-brand-700'
      : 'text-fg-secondary hover:bg-neutral-100 hover:text-fg'"
    :aria-label="label"
    :title="label"
  >
    <SIcon :name="icon" :size="16" />

    <!-- 自訂 tooltip（比 native title 更快、更穩） -->
    <span
      class="pointer-events-none absolute top-full left-1/2 -translate-x-1/2 mt-1.5 px-2 py-1
             text-xs font-medium rounded-md whitespace-nowrap shadow-lg
             bg-neutral-900 text-white opacity-0 group-hover:opacity-100
             transition-opacity duration-150 z-50"
    >{{ label }}</span>

    <!-- 底部 active 指示條（跟 HNavItem 一致） -->
    <span
      v-if="isActive"
      class="absolute left-2 right-2 -bottom-[7px] h-[2px] bg-brand-600 rounded-full"
    />
  </router-link>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { SIcon } from '@staffkm/ui-kit'

const props = defineProps<{
  to: string
  label: string
  icon: string
}>()
const route = useRoute()
const isActive = computed(() => route.path.startsWith(props.to))
</script>
