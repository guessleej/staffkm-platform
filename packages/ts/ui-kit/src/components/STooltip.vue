<template>
  <span class="relative inline-flex group">
    <slot/>
    <span v-if="content"
          :class="['absolute z-50 px-2 py-1 text-[11px] text-white bg-neutral-900 rounded shadow-lg pointer-events-none whitespace-nowrap',
                   'opacity-0 group-hover:opacity-100 transition-opacity delay-100',
                   pos === 'top'    ? 'bottom-full mb-1.5 left-1/2 -translate-x-1/2' :
                   pos === 'bottom' ? 'top-full mt-1.5 left-1/2 -translate-x-1/2' :
                   pos === 'left'   ? 'right-full mr-1.5 top-1/2 -translate-y-1/2' :
                                       'left-full ml-1.5 top-1/2 -translate-y-1/2']">
      {{ content }}
    </span>
  </span>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ content?: string; pos?: 'top'|'bottom'|'left'|'right' }>(), { pos: 'top' })
</script>
