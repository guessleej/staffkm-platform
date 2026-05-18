<template>
  <div class="min-h-screen flex items-center justify-center bg-surface-raised px-4">
    <div class="w-full max-w-md p-8 rounded-2xl border border-bd bg-surface-raised shadow-sm">
      <h1 class="text-2xl font-bold text-fg mb-1">忘記密碼</h1>
      <p class="text-sm text-fg-secondary mb-6">
        輸入你的 email；若該帳號存在，我們會寄送重設連結。
      </p>

      <form v-if="!sent" @submit.prevent="onSubmit" class="space-y-4">
        <div>
          <label class="block text-xs font-medium text-fg-secondary mb-1">Email</label>
          <input
            v-model="email" type="email" required autocomplete="email"
            class="w-full px-3 py-2 rounded-lg border border-bd bg-surface-raised text-fg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="you@company.com"
          />
        </div>

        <p v-if="errorMsg" class="text-sm text-rose-600">{{ errorMsg }}</p>

        <button
          type="submit" :disabled="loading || !email"
          class="w-full py-2.5 rounded-lg bg-indigo-600 text-white font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-indigo-500 transition"
        >
          {{ loading ? '送出中…' : '寄送重設連結' }}
        </button>
      </form>

      <div v-else class="p-4 rounded-lg bg-emerald-50 border border-emerald-200">
        <p class="text-sm text-emerald-900 font-medium mb-1">已送出</p>
        <p class="text-xs text-emerald-800">
          若 {{ email }} 已註冊，重設連結已寄出（有效 1 小時）。請檢查信箱（含垃圾信夾）。
        </p>
      </div>

      <p class="mt-6 text-center text-xs text-fg-tertiary">
        想起密碼了？
        <RouterLink to="/login" class="text-indigo-600 hover:underline">回登入</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { authApi } from '../../api/auth'

const email = ref('')
const loading = ref(false)
const sent = ref(false)
const errorMsg = ref('')

async function onSubmit() {
  errorMsg.value = ''
  loading.value = true
  try {
    await authApi.forgotPassword(email.value)
    sent.value = true
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.detail || '送出失敗，請稍後再試'
  } finally {
    loading.value = false
  }
}
</script>
