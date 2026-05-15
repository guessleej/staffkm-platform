<template>
  <router-link
    :to="to"
    :title="collapsed ? label : undefined"
    class="group relative flex items-center gap-3 rounded-lg text-sm font-medium transition-all"
    :class="[
      collapsed ? 'h-9 w-9 mx-auto justify-center' : 'h-9 px-3',
      isActive
        ? 'bg-brand-50 text-brand-700 shadow-sm'
        : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900',
    ]"
  >
    <!-- 左側 active indicator bar -->
    <span
      v-if="isActive && !collapsed"
      class="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-brand-600 rounded-r"
    ></span>
    <span class="text-base leading-none flex-shrink-0">
      <slot name="icon">{{ icon }}</slot>
    </span>
    <span v-if="!collapsed" class="truncate">{{ label }}</span>
    <span
      v-if="!collapsed && badge"
      class="ml-auto px-1.5 min-w-[18px] h-[18px] flex items-center justify-center text-[10px] font-semibold rounded-full"
      :class="isActive ? 'bg-brand-600 text-white' : 'bg-neutral-200 text-neutral-700'"
    >{{ badge }}</span>
  </router-link>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const props = defineProps<{
  to: string
  icon?: string
  label: string
  collapsed?: boolean
  badge?: string | number
}>()
const route = useRoute()
const isActive = computed(() => route.path.startsWith(props.to))
</script>
