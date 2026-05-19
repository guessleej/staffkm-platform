<template>
  <div class="min-h-screen bg-surface-base text-neutral-900 flex flex-col">
    <header class="h-12 px-6 flex items-center border-b border-neutral-100 flex-shrink-0">
      <div class="flex items-center gap-2 text-sm">
        <SIcon name="share-2" :size="14" class="text-brand-600" />
        <span class="font-medium">已分享的對話</span>
        <span class="text-neutral-400">（唯讀）</span>
      </div>
    </header>

    <main class="flex-1 overflow-y-auto">
      <div class="max-w-3xl mx-auto w-full px-6 py-8">
        <p v-if="loading" class="text-sm text-neutral-400">載入中…</p>
        <div v-else-if="error" class="text-center py-20 text-sm text-danger-600">
          {{ error }}
        </div>
        <template v-else-if="data">
          <h1 class="text-xl font-semibold mb-1">{{ data.title }}</h1>
          <p class="text-xs text-neutral-500 mb-8">分享於 {{ formatDate(data.created_at) }}</p>
          <article
            v-for="(m, i) in data.messages"
            :key="i"
            class="mb-6 text-[15px] leading-7"
          >
            <header class="mb-1 text-[11px] uppercase tracking-widest text-neutral-400">
              {{ m.role === 'user' ? '使用者' : 'staffKM' }}
            </header>
            <div
              class="whitespace-pre-wrap"
              :class="m.role === 'user' ? 'text-neutral-900' : 'text-neutral-800'"
            >{{ m.content }}</div>
            <div v-if="m.citations?.length" class="mt-2 flex flex-wrap gap-1.5">
              <span
                v-for="(c, j) in m.citations"
                :key="j"
                class="px-2 py-0.5 text-[11px] rounded-full bg-brand-50/60 text-brand-700 border border-brand-100"
              >{{ c.doc_name || '引用' }}</span>
            </div>
          </article>
        </template>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { SIcon } from '@staffkm/ui-kit'

interface PublicMsg {
  role: string
  content: string
  citations?: Array<{ doc_name?: string }>
  created_at: string
}
interface PublicConv {
  title: string
  created_at: string
  messages: PublicMsg[]
}

const route = useRoute()
const loading = ref(true)
const error = ref<string>('')
const data = ref<PublicConv | null>(null)

function formatDate(iso: string) {
  try { return new Date(iso).toLocaleString('zh-TW', { hour12: false }) } catch { return iso }
}

onMounted(async () => {
  const token = String(route.params.token || '')
  if (!token) { error.value = '分享連結缺少 token'; loading.value = false; return }
  try {
    const resp = await fetch(`/api/v1/public/conversations/${encodeURIComponent(token)}`)
    if (!resp.ok) { error.value = `連結無效或已撤銷（HTTP ${resp.status}）`; return }
    const body = await resp.json()
    data.value = body.data
  } catch (e: any) {
    error.value = '載入失敗：' + (e?.message || e)
  } finally {
    loading.value = false
  }
})
</script>
