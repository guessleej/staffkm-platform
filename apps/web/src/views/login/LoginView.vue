<template>
  <div class="h-screen flex overflow-hidden select-none">

    <!-- ══════════════════════════════════════════════
         左側：品牌視覺區
    ══════════════════════════════════════════════ -->
    <div
      class="hidden lg:flex lg:w-[54%] flex-col items-center justify-center relative overflow-hidden"
      style="background:linear-gradient(150deg,#07111f 0%,#0c2050 55%,#081428 100%)"
    >
      <!-- 網格背景 -->
      <div
        class="absolute inset-0 pointer-events-none"
        style="background-image:radial-gradient(circle at 1.5px 1.5px,rgba(255,255,255,0.045) 1.5px,transparent 0);background-size:36px 36px"
      ></div>

      <!-- 中心暈光 -->
      <div
        class="absolute rounded-full pointer-events-none"
        style="width:560px;height:560px;top:50%;left:50%;transform:translate(-50%,-50%);background:radial-gradient(circle,rgba(99,102,241,0.18) 0%,transparent 68%)"
      ></div>

      <!-- SVG 知識圖譜插圖 -->
      <div class="relative z-10 w-80 h-80 mb-10">
        <svg viewBox="0 0 320 320" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-full h-full">

          <!-- 同心圓軌道 -->
          <circle cx="160" cy="160" r="148" stroke="white" stroke-opacity="0.035" stroke-width="1"/>
          <circle cx="160" cy="160" r="108" stroke="white" stroke-opacity="0.055" stroke-width="1"/>
          <circle cx="160" cy="160" r="68"  stroke="white" stroke-opacity="0.08"  stroke-width="1.5"/>

          <!-- 連接線：中心 → 各節點 -->
          <line x1="160" y1="160" x2="62"  y2="76"  stroke="rgba(129,140,248,0.35)" stroke-width="1"/>
          <line x1="160" y1="160" x2="262" y2="72"  stroke="rgba(129,140,248,0.3)"  stroke-width="1"/>
          <line x1="160" y1="160" x2="292" y2="185" stroke="rgba(129,140,248,0.35)" stroke-width="1"/>
          <line x1="160" y1="160" x2="218" y2="278" stroke="rgba(129,140,248,0.28)" stroke-width="1"/>
          <line x1="160" y1="160" x2="68"  y2="262" stroke="rgba(129,140,248,0.32)" stroke-width="1"/>
          <line x1="160" y1="160" x2="26"  y2="175" stroke="rgba(129,140,248,0.22)" stroke-width="1"/>

          <!-- 節點間的交叉連線 -->
          <line x1="62"  y1="76"  x2="262" y2="72"  stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
          <line x1="262" y1="72"  x2="292" y2="185" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
          <line x1="292" y1="185" x2="218" y2="278" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
          <line x1="218" y1="278" x2="68"  y2="262" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
          <line x1="68"  y1="262" x2="26"  y2="175" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>

          <!-- 外圍主要節點 -->
          <circle cx="62"  cy="76"  r="14" fill="#6366f1" fill-opacity="0.12"/>
          <circle cx="62"  cy="76"  r="8"  fill="#6366f1" fill-opacity="0.85"/>

          <circle cx="262" cy="72"  r="11" fill="white"   fill-opacity="0.07"/>
          <circle cx="262" cy="72"  r="6"  fill="white"   fill-opacity="0.55"/>

          <circle cx="292" cy="185" r="17" fill="#818cf8" fill-opacity="0.13"/>
          <circle cx="292" cy="185" r="10" fill="#818cf8" fill-opacity="0.8"/>

          <circle cx="218" cy="278" r="12" fill="white"   fill-opacity="0.07"/>
          <circle cx="218" cy="278" r="7"  fill="white"   fill-opacity="0.5"/>

          <circle cx="68"  cy="262" r="15" fill="#6366f1" fill-opacity="0.11"/>
          <circle cx="68"  cy="262" r="9"  fill="#6366f1" fill-opacity="0.75"/>

          <circle cx="26"  cy="175" r="9"  fill="white"   fill-opacity="0.06"/>
          <circle cx="26"  cy="175" r="5"  fill="white"   fill-opacity="0.4"/>

          <!-- 二級小節點 -->
          <circle cx="118" cy="38"  r="3" fill="white"   fill-opacity="0.28"/>
          <circle cx="278" cy="128" r="2.5" fill="#6366f1" fill-opacity="0.6"/>
          <circle cx="236" cy="232" r="3" fill="white"   fill-opacity="0.22"/>
          <circle cx="40"  cy="118" r="2.5" fill="#6366f1" fill-opacity="0.5"/>
          <circle cx="140" cy="296" r="2" fill="white"   fill-opacity="0.18"/>
          <circle cx="186" cy="42"  r="2" fill="white"   fill-opacity="0.2"/>

          <!-- 中心光暈層次 -->
          <circle cx="160" cy="160" r="56" fill="#4f46e5" fill-opacity="0.07"/>
          <circle cx="160" cy="160" r="38" fill="#4f46e5" fill-opacity="0.12"/>
          <circle cx="160" cy="160" r="24" fill="#4f46e5" fill-opacity="0.35"/>
          <circle cx="160" cy="160" r="16" fill="#6366f1"/>
          <circle cx="160" cy="160" r="16" fill="white"   fill-opacity="0.18"/>

          <!-- 中心文件 icon -->
          <path d="M156 153 h8 M156 160 h8 M156 167 h5" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-opacity="0.9"/>
          <path d="M153 149 Q153 148 154 148 L162 148 L166 152 L166 171 Q166 172 165 172 L154 172 Q153 172 153 171 Z"
                stroke="white" stroke-width="1.4" stroke-linejoin="round" stroke-opacity="0.55"/>

          <!-- 脈衝動畫圓 -->
          <circle cx="160" cy="160" r="24" stroke="#6366f1" stroke-width="2" stroke-opacity="0.6" class="pulse-ring"/>
        </svg>
      </div>

      <!-- 品牌文字：全部置中 -->
      <div class="relative z-10 text-center space-y-3 px-10">
        <div class="flex items-center justify-center gap-2 mb-1">
          <div class="w-5 h-px bg-indigo-400/60"></div>
          <span class="text-indigo-300/70 text-xs tracking-[0.2em] uppercase font-medium">Knowledge Platform</span>
          <div class="w-5 h-px bg-indigo-400/60"></div>
        </div>
        <h1 class="text-5xl font-bold text-white tracking-tight">StaffKM</h1>
        <p class="text-blue-200/65 text-base">行政知識管理平台</p>
        <div class="flex items-center justify-center gap-4 pt-1">
          <span class="text-white/25 text-xs">公文查詢</span>
          <span class="text-white/15">·</span>
          <span class="text-white/25 text-xs">SOP 導引</span>
          <span class="text-white/15">·</span>
          <span class="text-white/25 text-xs">AI 問答</span>
        </div>
      </div>

      <!-- 底部版本標 -->
      <div class="absolute bottom-7 text-white/18 text-[11px] tracking-widest font-light">
        INTERNAL USE ONLY &nbsp;·&nbsp; v1.0.0
      </div>
    </div>

    <!-- ══════════════════════════════════════════════
         右側：登入表單區
    ══════════════════════════════════════════════ -->
    <div class="flex-1 relative flex flex-col bg-surface-raised">

      <!-- 頂部 Logo 錨點 -->
      <div class="flex items-center gap-3 px-10 pt-8 pb-0">
        <div class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
             style="background:linear-gradient(135deg,#4f46e5,#818cf8)">
          <SIcon name="file-text" :size="14" class="text-white" />
        </div>
        <span class="text-sm font-bold text-fg tracking-tight">StaffKM</span>
        <div class="w-px h-4 bg-neutral-200"></div>
        <span class="text-xs text-fg-tertiary">行政知識管理平台</span>
      </div>

      <!-- 中央表單（撐滿剩餘空間並置中） -->
      <div class="flex-1 flex flex-col items-center justify-center px-10">
        <div class="w-full max-w-[400px] space-y-7">

          <!-- 標題 -->
          <div class="space-y-2">
            <h2 class="text-[2rem] font-bold text-fg tracking-tight leading-tight">登入系統</h2>
            <p class="text-sm text-fg-tertiary">請輸入您的工號及密碼以繼續使用</p>
          </div>

          <!-- 表單 -->
          <form @submit.prevent="handleLogin" class="space-y-4" novalidate autocomplete="on">

          <!-- 帳號 -->
          <div class="space-y-1.5">
            <label for="username" class="block text-[13px] font-semibold text-fg-secondary tracking-wide">工號 / 帳號</label>
            <div class="relative group">
              <SIcon name="user" :size="16" :stroke-width="1.8"
                     class="absolute left-3.5 top-1/2 -translate-y-1/2 transition-colors group-focus-within:text-indigo-500 pointer-events-none"
                     :class="fieldError ? 'text-rose-400' : 'text-fg-tertiary'" />
              <input
                id="username"
                v-model="form.username"
                type="text"
                autocomplete="username"
                placeholder="請輸入帳號"
                :class="[
                  'w-full h-11 pl-10 pr-4 text-sm rounded-xl border transition-all duration-150 outline-none',
                  'placeholder:text-fg-tertiary text-fg bg-surface-sunken/80',
                  fieldError
                    ? 'border-rose-300 bg-rose-50/50 focus:ring-2 focus:ring-rose-200 focus:border-rose-400'
                    : 'border-neutral-200 focus:bg-surface-raised focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100'
                ]"
              />
            </div>
          </div>

          <!-- 密碼 -->
          <div class="space-y-1.5">
            <label for="password" class="block text-[13px] font-semibold text-fg-secondary tracking-wide">密碼</label>
            <div class="relative group">
              <SIcon name="lock" :size="16" :stroke-width="1.8"
                     class="absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none transition-colors"
                     :class="fieldError ? 'text-rose-400' : 'text-fg-tertiary group-focus-within:text-indigo-500'" />
              <input
                id="password"
                v-model="form.password"
                :type="showPwd ? 'text' : 'password'"
                autocomplete="current-password"
                placeholder="請輸入密碼"
                :class="[
                  'w-full h-11 pl-10 pr-11 text-sm rounded-xl border transition-all duration-150 outline-none',
                  'placeholder:text-fg-tertiary text-fg bg-surface-sunken/80',
                  fieldError
                    ? 'border-rose-300 bg-rose-50/50 focus:ring-2 focus:ring-rose-200 focus:border-rose-400'
                    : 'border-neutral-200 focus:bg-surface-raised focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100'
                ]"
              />
              <button
                type="button"
                @click="showPwd = !showPwd"
                class="absolute right-3.5 top-1/2 -translate-y-1/2 text-fg-tertiary hover:text-fg-secondary transition-colors p-0.5"
                :aria-label="showPwd ? '隱藏密碼' : '顯示密碼'"
              >
                <SIcon :name="showPwd ? 'eye-off' : 'eye'" :size="16" :stroke-width="1.8" class="text-fg-tertiary" />
              </button>
            </div>
          </div>

          <!-- 錯誤訊息 -->
          <Transition
            enter-active-class="transition-all duration-200 ease-out"
            enter-from-class="opacity-0 -translate-y-1.5 scale-98"
            enter-to-class="opacity-100 translate-y-0 scale-100"
            leave-active-class="transition-all duration-150 ease-in"
            leave-from-class="opacity-100 translate-y-0"
            leave-to-class="opacity-0 -translate-y-1"
          >
            <div v-if="errorMsg" class="flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl bg-rose-50 border border-rose-100">
              <SIcon name="alert-circle" :size="16" :stroke-width="2.2" class="text-rose-500 flex-shrink-0" />
              <p class="text-sm text-rose-700 font-medium">{{ errorMsg }}</p>
            </div>
          </Transition>

          <!-- Sprint 20-B：CAPTCHA challenge（3 次失敗後出現） -->
          <div v-if="captcha" class="space-y-1.5">
            <label for="cap" class="block text-[13px] font-semibold text-fg-secondary tracking-wide">
              驗證碼
              <button type="button" @click="fetchCaptcha"
                      class="ml-2 text-[11px] text-indigo-600 hover:underline">換一題</button>
            </label>
            <div class="flex items-center gap-2">
              <div class="px-3 h-11 rounded-xl bg-slate-50 border border-slate-200 flex items-center text-base font-mono text-slate-700 select-none">
                {{ captcha.question }}
              </div>
              <input
                id="cap"
                v-model="captchaAnswer"
                inputmode="numeric"
                autocomplete="off"
                placeholder="算式答案"
                class="flex-1 h-11 px-3 text-sm rounded-xl border border-slate-200 placeholder:text-slate-300 text-slate-800 bg-slate-50/80 focus:bg-surface-raised focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 outline-none"
              />
            </div>
          </div>

          <!-- 登入按鈕 -->
          <button
            type="submit"
            :disabled="loading || !form.username || !form.password"
            class="relative w-full h-11 rounded-xl text-sm font-semibold text-white overflow-hidden transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-45 disabled:cursor-not-allowed"
            style="background:linear-gradient(135deg,#4f46e5 0%,#6366f1 100%)"
            :style="!loading && form.username && form.password ? 'box-shadow:0 4px 15px rgba(99,102,241,0.35)' : ''"
          >
            <span v-if="!loading" class="flex items-center justify-center gap-2">
              <span>登入系統</span>
              <SIcon name="arrow-right" :size="16" :stroke-width="2.2" />
            </span>
            <span v-else class="flex items-center justify-center gap-2">
              <SSpinner :size="16" />
              驗證中…
            </span>
          </button>
        </form>

        <!-- 底部說明 -->
        <p class="text-center text-[12px] text-fg-tertiary leading-relaxed">
          忘記密碼或帳號異常，請聯繫
          <span class="text-indigo-600 font-medium cursor-default">資訊管理部門</span>
          協助重置
        </p>

      </div>
    </div>

  </div>

</div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { SIcon, SSpinner } from '@staffkm/ui-kit'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const form = ref({ username: '', password: '' })
const loading = ref(false)
const errorMsg = ref('')
const showPwd = ref(false)
const fieldError = computed(() => !!errorMsg.value)

// Sprint 20-B：CAPTCHA
import { authApi as _authApi, type Captcha } from '../../api/auth'
const captcha = ref<Captcha | null>(null)
const captchaAnswer = ref('')
async function fetchCaptcha() {
  try { captcha.value = await _authApi.getCaptcha(); captchaAnswer.value = '' }
  catch { captcha.value = null }
}

async function handleLogin() {
  errorMsg.value = ''
  loading.value = true
  try {
    const cap = captcha.value && captchaAnswer.value
      ? { token: captcha.value.token, answer: captchaAnswer.value.trim() }
      : undefined
    await auth.login(form.value.username, form.value.password, cap)
    const next = (route.query.next as string) || '/'
    router.push(next.startsWith('/') ? next : '/')
  } catch (err: any) {
    const detail = err.response?.data?.detail
    if (detail === 'captcha_required') {
      errorMsg.value = '請完成下方驗證碼後重新登入'
      await fetchCaptcha()
    } else if (detail === 'captcha_invalid') {
      errorMsg.value = '驗證碼錯誤，請重試'
      await fetchCaptcha()
    } else {
      errorMsg.value = detail ?? '帳號或密碼錯誤，請重新輸入'
      // 若已有 captcha 顯示中，重抓新題（避免 token 被重用）
      if (captcha.value) await fetchCaptcha()
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.pulse-ring {
  animation: pulse 2.8s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  transform-origin: 160px 160px;
}
@keyframes pulse {
  0%, 100% { opacity: 0.6; transform: scale(1); }
  50%       { opacity: 0.15; transform: scale(1.55); }
}
</style>
