<template>
  <div class="min-h-screen flex items-center justify-center bg-surface-raised px-4">
    <div class="w-full max-w-md p-8 rounded-2xl border border-bd bg-surface-raised shadow-sm">
      <h1 class="text-2xl font-bold text-fg mb-1">重設密碼</h1>
      <p class="text-sm text-fg-secondary mb-6">設定新密碼（至少 8 字元）。</p>

      <div v-if="!token" class="p-4 rounded-lg bg-rose-50 border border-rose-200">
        <p class="text-sm text-rose-700">缺少重設 token；請從 email 連結進入。</p>
      </div>

      <form v-else-if="!done" @submit.prevent="onSubmit" class="space-y-4">
        <div>
          <label class="block text-xs font-medium text-fg-secondary mb-1">新密碼</label>
          <input
            v-model="password" type="password" required minlength="8" autocomplete="new-password"
            class="w-full px-3 py-2 rounded-lg border border-bd bg-surface-raised text-fg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label class="block text-xs font-medium text-fg-secondary mb-1">確認密碼</label>
          <input
            v-model="confirm" type="password" required minlength="8" autocomplete="new-password"
            class="w-full px-3 py-2 rounded-lg border border-bd bg-surface-raised text-fg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <p v-if="errorMsg" class="text-sm text-rose-600">{{ errorMsg }}</p>

        <button
          type="submit" :disabled="loading || !canSubmit"
          class="w-full py-2.5 rounded-lg bg-indigo-600 text-white font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-indigo-500 transition"
        >
          {{ loading ? '更新中…' : '更新密碼' }}
        </button>
      </form>

      <div v-else class="p-4 rounded-lg bg-emerald-50 border border-emerald-200">
        <p class="text-sm text-emerald-900 font-medium mb-1">密碼已更新</p>
        <RouterLink to="/login" class="inline-block mt-2 text-sm text-indigo-600 font-medium hover:underline">
          前往登入 →
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { authApi } from '../../api/auth'

const route = useRoute()
const token = (route.query.token as string) || ''
const password = ref('')
const confirm = ref('')
const loading = ref(false)
const done = ref(false)
const errorMsg = ref('')

const canSubmit = computed(() => password.value.length >= 8 && password.value === confirm.value)

async function onSubmit() {
  errorMsg.value = ''
  if (password.value !== confirm.value) {
    errorMsg.value = '兩次密碼輸入不一致'
    return
  }
  loading.value = true
  try {
    await authApi.resetPassword(token, password.value)
    done.value = true
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.detail || '重設失敗，連結可能已失效'
  } finally {
    loading.value = false
  }
}
</script>
