<template>
  <IconBase v-bind="$attrs" class="animate-spin">
    <circle cx="12" cy="12" r="10" stroke-opacity="0.2"/>
    <path d="M22 12a10 10 0 0 1-10 10" />
  </IconBase>
</template>
<script setup lang="ts">import IconBase from './IconBase.vue'</script>
