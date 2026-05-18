<template>
  <div class="min-h-screen flex items-center justify-center bg-surface-raised px-4">
    <div class="w-full max-w-md p-8 rounded-2xl border border-bd bg-surface-raised shadow-sm text-center">
      <h1 class="text-xl font-bold text-fg mb-4">{{ provider }} 登入</h1>

      <p v-if="state === 'loading'" class="text-sm text-fg-secondary">處理中…</p>

      <div v-else-if="state === 'error'" class="space-y-3">
        <p class="text-sm text-rose-600">{{ errorMsg }}</p>
        <RouterLink to="/login" class="inline-block text-sm text-indigo-600 hover:underline">回登入頁</RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { http } from '../../api'
import { useAuthStore } from '../../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const provider = (route.params.provider as string) || ''
const state = ref<'loading' | 'error'>('loading')
const errorMsg = ref('')

onMounted(async () => {
  const code  = (route.query.code  as string) || ''
  const stateQ = (route.query.state as string) || ''
  if (!code || !provider) {
    state.value = 'error'
    errorMsg.value = '缺少 OAuth 授權碼'
    return
  }
  try {
    const { data } = await http.get(`/auth/oauth/${provider}/callback`, {
      params: { code, state: stateQ },
    })
    const d = data.data
    // 與 /auth/login 回傳結構一致：access_token / refresh_token / user
    await auth.setTokens(d.access_token, d.refresh_token, d.user)
    router.replace(d.is_new_user ? '/chat' : '/chat')
  } catch (e: any) {
    state.value = 'error'
    errorMsg.value = e?.response?.data?.detail || `${provider} 登入失敗`
  }
})
</script>
