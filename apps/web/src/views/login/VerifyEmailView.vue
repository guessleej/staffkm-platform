<template>
  <div class="min-h-screen flex items-center justify-center bg-surface-raised px-4">
    <div class="w-full max-w-md p-8 rounded-2xl border border-bd bg-surface-raised shadow-sm text-center">
      <h1 class="text-2xl font-bold text-fg mb-4">Email 驗證</h1>

      <p v-if="state === 'loading'" class="text-sm text-fg-secondary">驗證中…</p>

      <div v-else-if="state === 'success'" class="space-y-3">
        <div class="text-emerald-600 text-3xl">✓</div>
        <p class="text-sm text-fg">{{ email }} 驗證成功</p>
        <RouterLink to="/login" class="inline-block mt-2 text-sm text-indigo-600 font-medium hover:underline">
          前往登入 →
        </RouterLink>
      </div>

      <div v-else class="space-y-3">
        <div class="text-rose-600 text-3xl">✗</div>
        <p class="text-sm text-rose-600">{{ errorMsg }}</p>
        <RouterLink to="/login" class="inline-block mt-2 text-sm text-indigo-600 font-medium hover:underline">
          回登入頁
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { authApi } from '../../api/auth'

const route = useRoute()
const state = ref<'loading' | 'success' | 'error'>('loading')
const email = ref('')
const errorMsg = ref('')

onMounted(async () => {
  const token = (route.query.token as string) || ''
  if (!token) {
    state.value = 'error'
    errorMsg.value = '缺少驗證 token'
    return
  }
  try {
    const r = await authApi.confirmVerifyEmail(token)
    email.value = r.email
    state.value = 'success'
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.detail || '驗證連結已失效或無效'
    state.value = 'error'
  }
})
</script>
