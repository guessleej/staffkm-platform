<template>
  <router-link
    :to="to"
    class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition"
    :class="isActive
      ? 'bg-indigo-50 text-indigo-700'
      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'"
  >
    <span class="text-base leading-none">{{ icon }}</span>
    <span>{{ label }}</span>
  </router-link>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const props = defineProps<{ to: string; icon: string; label: string }>()
const route = useRoute()
const isActive = computed(() => route.path.startsWith(props.to))
</script>
