<template>
  <!--
    v5.1 Warm Enterprise — 通用空狀態
    Usage:
      <EmptyState
        icon="folder"
        title="尚無資料"
        description="先建立一個項目開始使用"
        action-label="新增"
        @action="onCreate"
      />
  -->
  <div class="flex flex-col items-center justify-center text-center py-16 px-6">
    <div
      class="w-16 h-16 rounded-full flex items-center justify-center mb-5"
      :style="{
        background:
          'linear-gradient(135deg, hsl(35 25% 95%), hsl(35 30% 92%))',
        boxShadow:
          'inset 0 1px 0 rgba(255,255,255,0.6), 0 1px 3px rgba(0,0,0,0.04)',
      }"
    >
      <SIcon :name="icon" :size="28" :stroke-width="1.6" class="text-fg-tertiary" />
    </div>
    <h3 class="text-lg font-semibold text-fg tracking-tight">{{ title }}</h3>
    <p
      v-if="description"
      class="mt-1.5 text-sm text-fg-tertiary leading-relaxed max-w-sm"
    >{{ description }}</p>
    <button
      v-if="actionLabel"
      class="btn btn-primary mt-6"
      @click="emit('action')"
    >
      <SIcon name="plus" :size="14" :stroke-width="2.5" />
      {{ actionLabel }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { SIcon } from '@staffkm/ui-kit'

defineProps<{
  icon: string
  title: string
  description?: string
  actionLabel?: string
}>()

const emit = defineEmits<{ (e: 'action'): void }>()
</script>
