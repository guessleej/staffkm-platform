<template>
  <div class="space-y-1.5">
    <details
      v-for="(tc, i) in calls"
      :key="i"
      class="rounded-lg border border-neutral-200 bg-neutral-50/60 group"
      :open="tc.status === 'running'"
    >
      <summary class="flex items-center gap-2 px-3 py-1.5 cursor-pointer select-none text-xs text-neutral-700 hover:bg-neutral-100/80 rounded-lg">
        <SIcon name="tool" :size="12" class="text-brand-600" />
        <span class="font-mono">{{ tc.name }}</span>
        <span v-if="tc.status === 'running'" class="ml-auto inline-flex items-center gap-1 text-[11px] text-brand-600">
          <span class="inline-block w-1.5 h-1.5 bg-brand-500 rounded-full animate-pulse"></span>
          Thinking…
        </span>
        <span v-else-if="tc.status === 'success'" class="ml-auto text-[11px] text-success-700 inline-flex items-center gap-1">
          <SIcon name="check" :size="10" /> 已完成
        </span>
        <span v-else class="ml-auto text-[11px] text-danger-700 inline-flex items-center gap-1">
          <SIcon name="alert-circle" :size="10" /> 失敗
        </span>
        <SIcon name="chevron-down" :size="10" class="text-neutral-400 transition group-open:rotate-180" />
      </summary>
      <div class="px-3 pb-2 pt-1 text-[11px] font-mono text-neutral-700 space-y-1.5">
        <div v-if="tc.input">
          <p class="text-[10px] uppercase tracking-widest text-neutral-400 mb-0.5">輸入</p>
          <pre class="whitespace-pre-wrap bg-surface-raised border border-neutral-100 rounded px-2 py-1 max-h-40 overflow-auto">{{ formatJson(tc.input) }}</pre>
        </div>
        <div v-if="tc.output != null">
          <p class="text-[10px] uppercase tracking-widest text-neutral-400 mb-0.5">輸出</p>
          <pre class="whitespace-pre-wrap bg-surface-raised border border-neutral-100 rounded px-2 py-1 max-h-40 overflow-auto">{{ formatJson(tc.output) }}</pre>
        </div>
        <p v-if="tc.error" class="text-danger-700">{{ tc.error }}</p>
      </div>
    </details>
  </div>
</template>

<script setup lang="ts">
import { SIcon } from '@staffkm/ui-kit'
import type { ToolCall } from '../../stores/conversation'

defineProps<{ calls: ToolCall[] }>()

function formatJson(v: unknown): string {
  try {
    if (typeof v === 'string') return v
    return JSON.stringify(v, null, 2)
  } catch {
    return String(v)
  }
}
</script>
