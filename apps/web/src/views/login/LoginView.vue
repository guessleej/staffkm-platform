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
    <div class="flex-1 relative flex flex-col bg-white">

      <!-- 頂部 Logo 錨點 -->
      <div class="flex items-center gap-3 px-10 pt-8 pb-0">
        <div class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
             style="background:linear-gradient(135deg,#4f46e5,#818cf8)">
          <svg class="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
        </div>
        <span class="text-sm font-bold text-slate-800 tracking-tight">StaffKM</span>
        <div class="w-px h-4 bg-slate-200"></div>
        <span class="text-xs text-slate-400">行政知識管理平台</span>
      </div>

      <!-- 中央表單（撐滿剩餘空間並置中） -->
      <div class="flex-1 flex flex-col items-center justify-center px-10">
        <div class="w-full max-w-[400px] space-y-7">

          <!-- 標題 -->
          <div class="space-y-2">
            <h2 class="text-[2rem] font-bold text-slate-900 tracking-tight leading-tight">登入系統</h2>
            <p class="text-sm text-slate-400">請輸入您的工號及密碼以繼續使用</p>
          </div>

          <!-- 表單 -->
          <form @submit.prevent="handleLogin" class="space-y-4" novalidate autocomplete="on">

          <!-- 帳號 -->
          <div class="space-y-1.5">
            <label for="username" class="block text-[13px] font-semibold text-slate-600 tracking-wide">工號 / 帳號</label>
            <div class="relative group">
              <svg class="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-350 transition-colors group-focus-within:text-indigo-500 pointer-events-none"
                   :class="fieldError ? 'text-rose-400' : 'text-slate-400'"
                   fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
              </svg>
              <input
                id="username"
                v-model="form.username"
                type="text"
                autocomplete="username"
                placeholder="請輸入帳號"
                :class="[
                  'w-full h-11 pl-10 pr-4 text-sm rounded-xl border transition-all duration-150 outline-none',
                  'placeholder:text-slate-300 text-slate-800 bg-slate-50/80',
                  fieldError
                    ? 'border-rose-300 bg-rose-50/50 focus:ring-2 focus:ring-rose-200 focus:border-rose-400'
                    : 'border-slate-200 focus:bg-white focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100'
                ]"
              />
            </div>
          </div>

          <!-- 密碼 -->
          <div class="space-y-1.5">
            <label for="password" class="block text-[13px] font-semibold text-slate-600 tracking-wide">密碼</label>
            <div class="relative group">
              <svg class="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none transition-colors"
                   :class="fieldError ? 'text-rose-400' : 'text-slate-400 group-focus-within:text-indigo-500'"
                   fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
                <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"/>
              </svg>
              <input
                id="password"
                v-model="form.password"
                :type="showPwd ? 'text' : 'password'"
                autocomplete="current-password"
                placeholder="請輸入密碼"
                :class="[
                  'w-full h-11 pl-10 pr-11 text-sm rounded-xl border transition-all duration-150 outline-none',
                  'placeholder:text-slate-300 text-slate-800 bg-slate-50/80',
                  fieldError
                    ? 'border-rose-300 bg-rose-50/50 focus:ring-2 focus:ring-rose-200 focus:border-rose-400'
                    : 'border-slate-200 focus:bg-white focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100'
                ]"
              />
              <button
                type="button"
                @click="showPwd = !showPwd"
                class="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-350 hover:text-slate-600 transition-colors p-0.5"
                :aria-label="showPwd ? '隱藏密碼' : '顯示密碼'"
              >
                <svg v-if="!showPwd" class="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                </svg>
                <svg v-else class="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88"/>
                </svg>
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
              <svg class="w-4 h-4 text-rose-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"/>
              </svg>
              <p class="text-sm text-rose-700 font-medium">{{ errorMsg }}</p>
            </div>
          </Transition>

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
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"/>
              </svg>
            </span>
            <span v-else class="flex items-center justify-center gap-2">
              <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
              驗證中…
            </span>
          </button>
        </form>

        <!-- 底部說明 -->
        <p class="text-center text-[12px] text-slate-400 leading-relaxed">
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
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const form = ref({ username: '', password: '' })
const loading = ref(false)
const errorMsg = ref('')
const showPwd = ref(false)
const fieldError = computed(() => !!errorMsg.value)

async function handleLogin() {
  errorMsg.value = ''
  loading.value = true
  try {
    await auth.login(form.value.username, form.value.password)
    router.push('/')
  } catch (err: any) {
    errorMsg.value = err.response?.data?.detail ?? '帳號或密碼錯誤，請重新輸入'
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
