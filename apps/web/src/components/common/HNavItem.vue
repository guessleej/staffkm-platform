<template>
  <router-link
    :to="to"
    class="group relative inline-flex items-center gap-2 h-9 px-3 rounded-lg text-sm font-medium transition-colors"
    :class="isActive
      ? 'bg-brand-50 text-brand-700'
      : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900'"
  >
    <span class="flex-shrink-0">
      <slot name="icon" />
    </span>
    <span class="truncate">{{ label }}</span>
    <span
      v-if="badge"
      class="ml-1 px-1.5 min-w-[18px] h-[18px] flex items-center justify-center text-[10px] font-semibold rounded-full"
      :class="isActive ? 'bg-brand-600 text-white' : 'bg-neutral-200 text-neutral-700'"
    >{{ badge }}</span>
    <!-- 底部 active 指示條 -->
    <span
      v-if="isActive"
      class="absolute left-2 right-2 -bottom-[7px] h-[2px] bg-brand-600 rounded-full"
    ></span>
  </router-link>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const props = defineProps<{
  to: string
  label: string
  badge?: string | number
}>()
const route = useRoute()
const isActive = computed(() => route.path.startsWith(props.to))
</script>
