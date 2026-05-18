<script setup lang="ts">
/**
 * Marketplace 詳情頁 — v4.10 J.
 * Public route：未登入仍可看詳情；install 與 rate 都要登入。
 */
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { marketplaceApi, type MarketplaceTemplateDetail } from '@/api/marketplace'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const tpl = ref<MarketplaceTemplateDetail | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

const rating = ref(5)
const comment = ref('')
const submittingRating = ref(false)
const ratingMsg = ref<string | null>(null)

const isLoggedIn = computed(() => auth.isAuthenticated)

async function load() {
  loading.value = true
  error.value = null
  try {
    tpl.value = await marketplaceApi.detail(route.params.id as string)
  } catch (e: any) {
    error.value = e?.response?.data?.detail || '載入失敗'
  } finally {
    loading.value = false
  }
}

function clickInstall() {
  if (!isLoggedIn.value) {
    // 未登入 → 帶 next 跳 login
    const next = `/marketplace/${route.params.id}`
    router.push(`/login?next=${encodeURIComponent(next)}`)
    return
  }
  // 已登入 → 提示去 app templates 安裝
  // 直接呼叫 v2.5 workspace install endpoint（http interceptor 會帶 X-Workspace-ID）
  // 注意：這裡只 redirect 到 app-templates marketplace 視窗，由它執行 install
  router.push({
    path: '/app-templates',
    query: { install: tpl.value?.id },
  })
}

async function submitRating() {
  if (!isLoggedIn.value || !tpl.value) return
  submittingRating.value = true
  ratingMsg.value = null
  try {
    await marketplaceApi.rate(tpl.value.id, rating.value, comment.value || undefined)
    ratingMsg.value = '評分已送出'
    await load()
  } catch (e: any) {
    ratingMsg.value = e?.response?.data?.detail || '評分失敗'
  } finally {
    submittingRating.value = false
  }
}

function ratingStars(avg: number | null): string {
  if (avg === null || avg === undefined) return '—'
  const full = Math.round(avg)
  return '★'.repeat(full) + '☆'.repeat(5 - full)
}

onMounted(load)
</script>

<template>
  <div class="min-h-screen bg-surface-raised text-fg">
    <header class="border-b border-bd px-6 py-4 flex items-center justify-between">
      <router-link to="/marketplace" class="text-sm text-fg-secondary hover:text-fg">
        ← 回 marketplace
      </router-link>
      <router-link v-if="!isLoggedIn" to="/login" class="text-sm text-brand-600">登入</router-link>
    </header>

    <main class="max-w-4xl mx-auto px-6 py-8">
      <div v-if="loading" class="text-center py-12 text-fg-secondary">載入中...</div>
      <div v-else-if="error" class="text-center py-12 text-danger-600">{{ error }}</div>

      <article v-else-if="tpl">
        <div
          v-if="tpl.cover_image_url"
          class="aspect-video rounded-lg overflow-hidden mb-6 bg-neutral-200"
        >
          <img :src="tpl.cover_image_url" :alt="tpl.name" class="w-full h-full object-cover" />
        </div>

        <header class="flex items-start gap-4 mb-4">
          <div class="flex-1">
            <h1 class="text-3xl font-bold mb-2 flex items-center gap-2">
              {{ tpl.name }}
              <span
                v-if="tpl.verified"
                class="text-sm px-2 py-0.5 rounded bg-brand-50 text-brand-700"
              >✓ 官方驗證</span>
            </h1>
            <p class="text-fg-secondary">
              by {{ tpl.publisher_name || '匿名' }} · {{ tpl.license || 'MIT' }}
            </p>
          </div>
          <button
            class="px-4 py-2 rounded-lg bg-brand-600 text-white hover:bg-brand-700"
            @click="clickInstall"
          >
            {{ isLoggedIn ? 'Install to my workspace' : '登入後安裝' }}
          </button>
        </header>

        <div class="flex flex-wrap gap-4 mb-6 text-sm text-fg-secondary">
          <span>{{ tpl.install_count }} installs</span>
          <span class="text-warning-600">
            {{ ratingStars(tpl.rating_avg) }}
            ({{ tpl.rating_count }})
          </span>
          <span v-if="tpl.category">分類：{{ tpl.category }}</span>
        </div>

        <div v-if="tpl.tags?.length" class="flex flex-wrap gap-2 mb-6">
          <span
            v-for="t in tpl.tags"
            :key="t"
            class="text-xs px-2 py-1 rounded-full bg-neutral-200 text-fg-secondary"
          >#{{ t }}</span>
        </div>

        <section class="prose prose-sm max-w-none mb-8">
          <h2 class="text-lg font-semibold mb-2">介紹</h2>
          <p class="whitespace-pre-wrap text-fg">{{ tpl.description || '（無描述）' }}</p>
        </section>

        <section class="border-t border-bd pt-6 mb-8">
          <h2 class="text-lg font-semibold mb-3">評分</h2>
          <div v-if="!isLoggedIn" class="text-sm text-fg-secondary">
            <router-link to="/login" class="text-brand-600">登入</router-link> 後即可評分
          </div>
          <form v-else @submit.prevent="submitRating" class="space-y-3">
            <div class="flex items-center gap-2">
              <label class="text-sm">分數：</label>
              <select v-model.number="rating" class="px-2 py-1 rounded border border-bd bg-surface-raised">
                <option v-for="n in 5" :key="n" :value="n">{{ n }} 星</option>
              </select>
            </div>
            <textarea
              v-model="comment"
              rows="3"
              placeholder="留言（選填，2000 字內）"
              maxlength="2000"
              class="w-full px-3 py-2 rounded border border-bd bg-surface-raised"
            />
            <div class="flex items-center gap-3">
              <button
                type="submit"
                :disabled="submittingRating"
                class="px-3 py-1.5 rounded bg-brand-600 text-white disabled:opacity-50"
              >送出評分</button>
              <span v-if="ratingMsg" class="text-sm text-fg-secondary">{{ ratingMsg }}</span>
            </div>
          </form>
        </section>

        <section v-if="tpl.recent_ratings?.length" class="border-t border-bd pt-6">
          <h2 class="text-lg font-semibold mb-3">最新評論</h2>
          <ul class="space-y-3">
            <li
              v-for="r in tpl.recent_ratings"
              :key="r.user_id + r.created_at"
              class="rounded border border-bd p-3"
            >
              <div class="flex items-center justify-between text-xs text-fg-secondary mb-1">
                <span class="text-warning-600">{{ '★'.repeat(r.rating) }}{{ '☆'.repeat(5 - r.rating) }}</span>
                <span>{{ new Date(r.created_at).toLocaleString() }}</span>
              </div>
              <p v-if="r.comment" class="text-sm text-fg whitespace-pre-wrap">{{ r.comment }}</p>
              <p v-else class="text-sm text-fg-secondary italic">（無留言）</p>
            </li>
          </ul>
        </section>
      </article>
    </main>
  </div>
</template>
