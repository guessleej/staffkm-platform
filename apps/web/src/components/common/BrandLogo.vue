<!--
  v5.0.16 BrandLogo — 共用 logo 元件
  - 預設 size=44 (header 用)
  - LoginView 可以放大用
  - 圖案：堆疊文件 + 知識節點 spark，跟 favicon.svg 同一視覺語言
-->
<template>
  <svg
    :width="size" :height="size" viewBox="0 0 64 64"
    xmlns="http://www.w3.org/2000/svg" aria-hidden="true"
    class="flex-shrink-0"
  >
    <defs>
      <linearGradient :id="`brand-bg-${uid}`" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%"  stop-color="hsl(248, 92%, 64%)"/>
        <stop offset="55%" stop-color="hsl(239, 78%, 54%)"/>
        <stop offset="100%" stop-color="hsl(232, 62%, 38%)"/>
      </linearGradient>
      <linearGradient :id="`brand-sheet-${uid}`" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%"  stop-color="#ffffff" stop-opacity="1"/>
        <stop offset="100%" stop-color="#ffffff" stop-opacity="0.78"/>
      </linearGradient>
    </defs>
    <rect width="64" height="64" rx="15" :fill="`url(#brand-bg-${uid})`"/>
    <rect x="2" y="2" width="60" height="60" rx="13" fill="none"
          stroke="#ffffff" stroke-opacity="0.10" stroke-width="1"/>
    <g transform="translate(12 18)">
      <rect x="6"  y="0"  width="28" height="20" rx="3.5" fill="#ffffff" fill-opacity="0.40"/>
      <rect x="3"  y="6"  width="34" height="20" rx="3.5" fill="#ffffff" fill-opacity="0.65"/>
      <rect x="0"  y="12" width="40" height="20" rx="4"   :fill="`url(#brand-sheet-${uid})`"/>
      <rect x="5"  y="19" width="22" height="2.4" rx="1.2" fill="hsl(239, 72%, 48%)" fill-opacity="0.85"/>
      <rect x="5"  y="24" width="16" height="2.4" rx="1.2" fill="hsl(239, 72%, 48%)" fill-opacity="0.55"/>
    </g>
    <g transform="translate(44 12)">
      <circle cx="0" cy="0" r="6"   fill="#ffffff" fill-opacity="0.18"/>
      <circle cx="0" cy="0" r="3.4" fill="#ffffff"/>
    </g>
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'

withDefaults(defineProps<{ size?: number | string }>(), { size: 44 })

// 不同 instance gradient id 不能撞，否則 SVG 會互相覆蓋
const uid = computed(() => Math.random().toString(36).slice(2, 8))
</script>
