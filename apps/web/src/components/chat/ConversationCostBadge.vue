<template>
  <span v-if="cost > 0" class="text-xs text-fg-tertiary" :title="`${calls} 次 LLM 呼叫`">
    💰 ${{ cost.toFixed(4) }} · 🔤 {{ tokens.toLocaleString() }} ({{ calls }} calls)
  </span>
</template>

<script setup lang="ts">
// v3.7 P1：對話 cost 徽章 — lazy load `/conversations/{id}/cost`，顯示 total tokens / cost / call 次數
import { ref, watch, onMounted } from 'vue'
import { http } from '@/api'

const props = defineProps<{ conversationId: string | undefined | null }>()
const cost = ref(0)
const tokens = ref(0)
const calls = ref(0)

async function load() {
  if (!props.conversationId) {
    cost.value = 0
    tokens.value = 0
    calls.value = 0
    return
  }
  try {
    const r = await http.get(`/conversations/${props.conversationId}/cost`)
    const t = r.data?.data?.total ?? {}
    cost.value = Number(t.cost ?? 0)
    tokens.value = Number(t.tokens ?? 0)
    calls.value = Number(t.calls ?? 0)
  } catch {
    // 拿不到就靜默；不擋 UI
  }
}

watch(() => props.conversationId, load)
onMounted(load)
</script>
