<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0"
      leave-active-class="transition duration-200 ease-in"
      leave-to-class="opacity-0"
    >
      <div v-if="show" class="fixed inset-0 z-[60] flex items-center justify-center bg-neutral-900/60 backdrop-blur-md p-4">
        <div class="w-full max-w-2xl bg-surface-raised rounded-3xl shadow-2xl overflow-hidden">
          <!-- 進度條 -->
          <div class="h-1 bg-neutral-100">
            <div class="h-full bg-brand-600 transition-all duration-300"
                 :style="{ width: ((step / TOTAL_STEPS) * 100) + '%' }"></div>
          </div>

          <!-- Step 1: Welcome -->
          <div v-if="step === 1" class="p-10 text-center">
            <div class="text-6xl mb-6">👋</div>
            <h2 class="text-2xl font-bold text-fg mb-2">歡迎來到 staffKM</h2>
            <p class="text-base text-fg-secondary mb-1">
              企業 AI 知識管理平台 — 把規章 / SOP / 客服知識變成可問答的助理
            </p>
            <p class="text-sm text-fg-tertiary mb-8">
              30 秒帶你建好第一個應用 + 看看它怎麼運作
            </p>

            <div class="grid grid-cols-3 gap-3 mb-8 text-left">
              <div class="p-3 bg-brand-50/40 rounded-xl border border-brand-100">
                <div class="text-2xl mb-1">📚</div>
                <p class="text-sm font-semibold text-fg">知識庫</p>
                <p class="text-[11px] text-fg-tertiary mt-0.5">上傳文件、自動切片、向量檢索</p>
              </div>
              <div class="p-3 bg-brand-50/40 rounded-xl border border-brand-100">
                <div class="text-2xl mb-1">🤖</div>
                <p class="text-sm font-semibold text-fg">AI 應用</p>
                <p class="text-[11px] text-fg-tertiary mt-0.5">12+ 模板 / 自訂 prompt / workflow</p>
              </div>
              <div class="p-3 bg-brand-50/40 rounded-xl border border-brand-100">
                <div class="text-2xl mb-1">💬</div>
                <p class="text-sm font-semibold text-fg">對話</p>
                <p class="text-[11px] text-fg-tertiary mt-0.5">RAG 檢索 + 引用來源 + 串流</p>
              </div>
            </div>

            <button @click="next"
                    class="px-6 py-2.5 bg-brand-600 text-white text-sm font-semibold rounded-xl hover:bg-brand-700 transition">
              開始導覽 →
            </button>
            <p class="mt-3">
              <button @click="skip" class="text-xs text-fg-tertiary hover:text-fg underline">
                我熟了，直接進去
              </button>
            </p>
          </div>

          <!-- Step 2: pick start path -->
          <div v-if="step === 2" class="p-10">
            <h2 class="text-xl font-bold text-fg text-center mb-2">第一個應用，怎麼開？</h2>
            <p class="text-sm text-fg-tertiary text-center mb-8">兩條路、都很快</p>

            <div class="grid grid-cols-2 gap-4 mb-6">
              <button @click="goTemplate"
                      class="group p-6 text-left bg-brand-50/30 border-2 border-brand-200 hover:border-brand-400 hover:bg-brand-50/60 rounded-2xl transition">
                <div class="text-4xl mb-3">✨</div>
                <p class="font-bold text-fg mb-1">從模板</p>
                <p class="text-xs text-fg-secondary">
                  6 個拿來即用：客服 FAQ / SQL / 合約審閱 / 內訓 / 翻譯 / 內部問答
                </p>
                <p class="mt-3 text-xs text-brand-700 font-semibold opacity-0 group-hover:opacity-100 transition">
                  推薦 →
                </p>
              </button>

              <button @click="goBlank"
                      class="group p-6 text-left bg-neutral-50 border-2 border-neutral-200 hover:border-neutral-400 rounded-2xl transition">
                <div class="text-4xl mb-3">⚡</div>
                <p class="font-bold text-fg mb-1">空白應用</p>
                <p class="text-xs text-fg-secondary">
                  自己寫 system prompt / 開場白 / 範例問題
                </p>
              </button>
            </div>

            <div class="flex items-center justify-between">
              <button @click="step = 1" class="text-xs text-fg-tertiary hover:text-fg">← 上一步</button>
              <button @click="skip" class="text-xs text-fg-tertiary hover:text-fg underline">
                跳過
              </button>
            </div>
          </div>

          <!-- Step 3: KB hint -->
          <div v-if="step === 3" class="p-10">
            <div class="text-center mb-6">
              <div class="text-5xl mb-3">📚</div>
              <h2 class="text-xl font-bold text-fg mb-2">想讓 AI 回答你公司的事？</h2>
              <p class="text-sm text-fg-tertiary">需要先建一個知識庫餵文件</p>
            </div>

            <div class="bg-neutral-50 rounded-xl p-5 mb-6 text-sm space-y-2 text-fg-secondary">
              <p class="flex items-start gap-2"><span class="text-brand-600">1.</span> 進「知識庫」分頁 →「建立知識庫」</p>
              <p class="flex items-start gap-2"><span class="text-brand-600">2.</span> 拖檔上傳（PDF / Word / Markdown / Excel）</p>
              <p class="flex items-start gap-2"><span class="text-brand-600">3.</span> 等切片 + 向量化（看 size 30 秒～ 5 分鐘）</p>
              <p class="flex items-start gap-2"><span class="text-brand-600">4.</span> 建應用時把這 KB 勾起來</p>
            </div>

            <p class="text-[11px] text-fg-tertiary text-center mb-6">
              💡 之後也可以從「✨ 從模板建立」→ 模板自動帶 prompt + 你選 KB
            </p>

            <div class="flex items-center justify-between">
              <button @click="step = 2" class="text-xs text-fg-tertiary hover:text-fg">← 上一步</button>
              <div class="flex items-center gap-2">
                <button @click="goKnowledge"
                        class="px-4 py-2 text-sm font-medium text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50">
                  去建知識庫
                </button>
                <button @click="finish"
                        class="px-4 py-2 text-sm font-semibold text-white bg-brand-600 rounded-lg hover:bg-brand-700">
                  完成導覽
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'

const STORAGE_KEY = 'staffkm.onboarding.done'
const TOTAL_STEPS = 3
const show = ref(false)
const step = ref(1)

const router = useRouter()
const auth = useAuthStore()

function shouldShow(): boolean {
  if (localStorage.getItem(STORAGE_KEY) === '1') return false
  // 只在已登入時跑
  if (!auth.user) return false
  return true
}

function markDone() {
  localStorage.setItem(STORAGE_KEY, '1')
}

function next() { step.value = Math.min(step.value + 1, TOTAL_STEPS) }
function skip() { markDone(); show.value = false }
function finish() { markDone(); show.value = false }

function goTemplate() {
  markDone(); show.value = false
  // 開模板畫廊 — 直接帶 query param 讓 ApplicationListView 自動開
  router.push({ path: '/applications', query: { tour: 'templates' } })
}
function goBlank() {
  markDone(); show.value = false
  router.push({ path: '/applications', query: { tour: 'create' } })
}
function goKnowledge() {
  markDone(); show.value = false
  router.push('/knowledge')
}

onMounted(() => {
  if (shouldShow()) {
    // 給 layout 一拍渲染
    setTimeout(() => { show.value = true }, 300)
  }
})

// 外部呼叫 force open（settings menu 「重看導覽」）
defineExpose({
  open() { step.value = 1; show.value = true },
})
</script>
