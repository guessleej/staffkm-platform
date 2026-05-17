<template>
  <div :class="['animate-pulse bg-neutral-200/70 rounded',
                variant === 'text'   ? 'h-3 w-3/4' :
                variant === 'title'  ? 'h-5 w-1/2' :
                variant === 'avatar' ? 'h-10 w-10 rounded-full' :
                variant === 'card'   ? 'h-32 w-full rounded-xl' : '']"
       :style="customStyle"/>
</template>

<script setup lang="ts">
import { computed } from 'vue'
const props = withDefaults(defineProps<{
  variant?: 'text' | 'title' | 'avatar' | 'card' | 'custom'
  width?:   string  // 任意 css width
  height?:  string
}>(), { variant: 'text' })
const customStyle = computed(() => ({
  ...(props.width  ? { width:  props.width  } : {}),
  ...(props.height ? { height: props.height } : {}),
}))
</script>
