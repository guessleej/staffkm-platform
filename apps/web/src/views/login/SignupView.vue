<template>
  <div class="min-h-screen flex items-center justify-center bg-surface-raised px-4">
    <div class="w-full max-w-md p-8 rounded-2xl border border-bd bg-surface-raised shadow-sm">
      <h1 class="text-2xl font-bold text-fg mb-1">開立 14 天免費試用</h1>
      <p class="text-sm text-fg-secondary mb-6">
        建立工作區與管理員帳號，立即開始導入 staffKM。
      </p>

      <form @submit.prevent="onSubmit" class="space-y-4">
        <div>
          <label class="block text-xs font-medium text-fg-secondary mb-1">公司 Email</label>
          <input
            v-model="form.email" type="email" required autocomplete="email"
            class="w-full px-3 py-2 rounded-lg border border-bd bg-surface-raised text-fg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="you@company.com"
          />
        </div>

        <div>
          <label class="block text-xs font-medium text-fg-secondary mb-1">工作區名稱</label>
          <input
            v-model="form.workspace_name" type="text" required minlength="2" maxlength="64"
            class="w-full px-3 py-2 rounded-lg border border-bd bg-surface-raised text-fg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="例如：ACME Corp"
          />
        </div>

        <div>
          <label class="block text-xs font-medium text-fg-secondary mb-1">密碼（至少 8 字元）</label>
          <input
            v-model="form.password" type="password" required minlength="8" autocomplete="new-password"
            class="w-full px-3 py-2 rounded-lg border border-bd bg-surface-raised text-fg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <div>
          <label class="block text-xs font-medium text-fg-secondary mb-1">確認密碼</label>
          <input
            v-model="form.confirm" type="password" required minlength="8" autocomplete="new-password"
            class="w-full px-3 py-2 rounded-lg border border-bd bg-surface-raised text-fg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <p v-if="errorMsg" class="text-sm text-rose-600">{{ errorMsg }}</p>

        <button
          type="submit" :disabled="loading || !canSubmit"
          class="w-full py-2.5 rounded-lg bg-indigo-600 text-white font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-indigo-500 transition"
        >
          {{ loading ? '建立中…' : '開始 14 天試用' }}
        </button>
      </form>

      <div v-if="success" class="mt-6 p-4 rounded-lg bg-emerald-50 border border-emerald-200">
        <p class="text-sm text-emerald-900 font-medium mb-1">試用已開通</p>
        <p class="text-xs text-emerald-800">
          到期：{{ formatDate(success.trial_expires_at) }}
        </p>
        <RouterLink to="/login" class="inline-block mt-2 text-sm text-indigo-600 font-medium hover:underline">
          前往登入 →
        </RouterLink>
      </div>

      <p class="mt-6 text-center text-xs text-fg-tertiary">
        已有帳號？
        <RouterLink to="/login" class="text-indigo-600 hover:underline">登入</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { authApi } from '../../api/auth'

const form = reactive({ email: '', workspace_name: '', password: '', confirm: '' })
const loading = ref(false)
const errorMsg = ref('')
const success = ref<{ trial_expires_at: string; workspace_id: string } | null>(null)

const canSubmit = computed(() =>
  !!form.email && !!form.workspace_name &&
  form.password.length >= 8 && form.password === form.confirm
)

function formatDate(iso: string): string {
  try { return new Date(iso).toLocaleString('zh-TW') } catch { return iso }
}

async function onSubmit() {
  errorMsg.value = ''
  if (form.password !== form.confirm) {
    errorMsg.value = '兩次密碼輸入不一致'
    return
  }
  loading.value = true
  try {
    const r = await authApi.trialSignup({
      email: form.email,
      password: form.password,
      workspace_name: form.workspace_name,
    })
    success.value = r
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.detail || e?.message || '註冊失敗，請稍後再試'
  } finally {
    loading.value = false
  }
}
</script>
