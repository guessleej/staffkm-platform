<template>
  <div class="min-h-screen flex items-center justify-center bg-surface-raised px-4">
    <div class="w-full max-w-md p-8 rounded-2xl border border-bd bg-surface-raised shadow-sm">
      <h1 class="text-2xl font-bold text-fg mb-1">設定新密碼</h1>
      <p class="text-sm text-fg-secondary mb-6">為了帳號安全，首次登入請更改預設密碼後再繼續使用。</p>

      <form @submit.prevent="onSubmit" class="space-y-4">
        <div>
          <label class="block text-xs font-medium text-fg-secondary mb-1">目前密碼</label>
          <input
            v-model="current" type="password" required autocomplete="current-password"
            class="w-full px-3 py-2 rounded-lg border border-bd bg-surface-raised text-fg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label class="block text-xs font-medium text-fg-secondary mb-1">新密碼（至少 8 字元）</label>
          <input
            v-model="next1" type="password" required minlength="8" autocomplete="new-password"
            class="w-full px-3 py-2 rounded-lg border border-bd bg-surface-raised text-fg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label class="block text-xs font-medium text-fg-secondary mb-1">確認新密碼</label>
          <input
            v-model="next2" type="password" required minlength="8" autocomplete="new-password"
            class="w-full px-3 py-2 rounded-lg border border-bd bg-surface-raised text-fg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <p v-if="errorMsg" class="text-sm text-danger-600">{{ errorMsg }}</p>

        <button
          type="submit" :disabled="loading || !canSubmit"
          class="w-full py-2.5 rounded-lg bg-indigo-600 text-white font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-indigo-500 transition"
        >
          {{ loading ? '更新中…' : '更新密碼並繼續' }}
        </button>
      </form>

      <button
        @click="onLogout"
        class="mt-4 w-full text-xs text-fg-tertiary hover:text-fg-secondary transition"
      >
        改用其他帳號登入
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '../../api/auth'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const current = ref('')
const next1 = ref('')
const next2 = ref('')
const loading = ref(false)
const errorMsg = ref('')

const canSubmit = computed(
  () => current.value.length > 0 && next1.value.length >= 8 && next1.value === next2.value,
)

async function onSubmit() {
  errorMsg.value = ''
  if (next1.value !== next2.value) {
    errorMsg.value = '兩次新密碼輸入不一致'
    return
  }
  if (next1.value === current.value) {
    errorMsg.value = '新密碼不可與目前密碼相同'
    return
  }
  loading.value = true
  try {
    await authApi.changePassword(current.value, next1.value)
    auth.clearMustChangePassword()
    router.push('/')
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.detail || e?.response?.data?.message || '更新失敗，請確認目前密碼是否正確'
  } finally {
    loading.value = false
  }
}

function onLogout() {
  auth.logout()
  router.push('/login')
}
</script>
