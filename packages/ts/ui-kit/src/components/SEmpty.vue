<template>
  <div :class="containerClasses">
    <!-- 預設視覺：iso 風格抽屜插畫；caller 可 slot 覆寫 -->
    <div :class="['mb-4 flex items-center justify-center rounded-2xl bg-neutral-50 border border-neutral-100', iconWrapperClasses]">
      <slot name="icon">
        <svg v-if="variant === 'box'" viewBox="0 0 120 120" fill="none" class="w-3/5 h-3/5" aria-hidden="true">
          <!-- 紙箱 iso 視角 -->
          <path d="M20 50 L60 30 L100 50 L60 70 Z" fill="hsl(var(--color-neutral-200))"/>
          <path d="M20 50 L20 85 L60 105 L60 70 Z" fill="hsl(var(--color-neutral-300))"/>
          <path d="M60 70 L60 105 L100 85 L100 50 Z" fill="hsl(var(--color-neutral-200))"/>
          <path d="M40 40 L60 30 L80 40 L60 50 Z" fill="hsl(var(--color-brand-300))" opacity="0.6"/>
        </svg>
        <svg v-else-if="variant === 'search'" viewBox="0 0 120 120" fill="none" class="w-3/5 h-3/5" aria-hidden="true">
          <circle cx="50" cy="50" r="28" stroke="hsl(var(--color-neutral-300))" stroke-width="4" fill="none"/>
          <line x1="72" y1="72" x2="92" y2="92" stroke="hsl(var(--color-neutral-300))" stroke-width="5" stroke-linecap="round"/>
          <circle cx="50" cy="50" r="14" fill="hsl(var(--color-brand-200))"/>
        </svg>
        <svg v-else-if="variant === 'doc'" viewBox="0 0 120 120" fill="none" class="w-3/5 h-3/5" aria-hidden="true">
          <rect x="30" y="20" width="60" height="80" rx="6" fill="hsl(var(--color-neutral-100))" stroke="hsl(var(--color-neutral-300))" stroke-width="2"/>
          <line x1="42" y1="44" x2="78" y2="44" stroke="hsl(var(--color-neutral-300))" stroke-width="3" stroke-linecap="round"/>
          <line x1="42" y1="58" x2="78" y2="58" stroke="hsl(var(--color-neutral-300))" stroke-width="3" stroke-linecap="round"/>
          <line x1="42" y1="72" x2="62" y2="72" stroke="hsl(var(--color-neutral-300))" stroke-width="3" stroke-linecap="round"/>
        </svg>
        <svg v-else viewBox="0 0 120 120" fill="none" class="w-3/5 h-3/5" aria-hidden="true">
          <!-- 預設：plus -->
          <circle cx="60" cy="60" r="40" stroke="hsl(var(--color-neutral-300))" stroke-width="3" stroke-dasharray="6 6" fill="hsl(var(--color-neutral-100))"/>
          <line x1="60" y1="44" x2="60" y2="76" stroke="hsl(var(--color-brand-400))" stroke-width="4" stroke-linecap="round"/>
          <line x1="44" y1="60" x2="76" y2="60" stroke="hsl(var(--color-brand-400))" stroke-width="4" stroke-linecap="round"/>
        </svg>
      </slot>
    </div>
    <h3 v-if="title" class="text-h4 text-fg mb-1">{{ title }}</h3>
    <p v-if="description" class="text-caption max-w-md">{{ description }}</p>
    <div v-if="$slots.action" class="mt-5">
      <slot name="action" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  title?:       string
  description?: string
  size?:        'sm' | 'md' | 'lg'
  /** 預設插畫：plus / box / search / doc。caller 可用 slot=icon 完全覆寫 */
  variant?:     'plus' | 'box' | 'search' | 'doc'
}>(), { size: 'md', variant: 'plus' })

const containerClasses = computed(() => [
  'flex flex-col items-center justify-center text-center',
  props.size === 'sm' ? 'py-8'  : props.size === 'lg' ? 'py-20' : 'py-14',
])
const iconWrapperClasses = computed(() => ({
  sm: 'w-16 h-16',
  md: 'w-24 h-24',
  lg: 'w-32 h-32',
}[props.size]))
</script>
