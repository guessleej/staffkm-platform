<script setup lang="ts">
/**
 * Marketplace 首頁 — v4.10 J.
 * Public route：不需登入也能瀏覽。
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'

import {
  marketplaceApi,
  type MarketplaceTemplate,
  type CategoryItem,
  type SortOption,
} from '@/api/marketplace'

const router = useRouter()

const loading = ref(false)
const items = ref<MarketplaceTemplate[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20

const search = ref('')
const category = ref<string | null>(null)
const sort = ref<SortOption>('popular')
const categories = ref<CategoryItem[]>([])

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

async function load() {
  loading.value = true
  try {
    const r = await marketplaceApi.list({
      category: category.value || undefined,
      search:   search.value || undefined,
      sort:     sort.value,
      page:     page.value,
      page_size: pageSize,
    })
    items.value = r.items
    total.value = r.total
  } finally {
    loading.value = false
  }
}

async function loadCategories() {
  categories.value = await marketplaceApi.categories()
}

function goDetail(id: string) {
  router.push({ name: 'marketplace-detail', params: { id } })
}

function ratingStars(avg: number | null): string {
  if (avg === null || avg === undefined) return '—'
  const full = Math.round(avg)
  return '★'.repeat(full) + '☆'.repeat(5 - full)
}

watch([category, sort], () => {
  page.value = 1
  load()
})

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(search, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    load()
  }, 300)
})

onMounted(() => {
  loadCategories()
  load()
})
</script>

<template>
  <div class="min-h-screen bg-surface-raised text-fg">
    <header class="border-b border-bd px-6 py-4 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <span class="text-xl font-bold">staffKM</span>
        <span class="text-fg-secondary">Workflow Marketplace</span>
      </div>
      <router-link
        to="/login"
        class="text-sm text-brand-600 hover:text-brand-700"
      >
        登入安裝 →
      </router-link>
    </header>

    <section class="max-w-6xl mx-auto px-6 py-8">
      <div class="card-hero mb-6">
        <h1 class="heading-page heading-accent">探索公開 workflow 模板</h1>
        <p class="text-fg-secondary mt-2">
          跨組織共享的 workflow gallery — 瀏覽不需登入，登入後即可一鍵 install 到你的 workspace。
        </p>
      </div>

      <div class="flex flex-wrap gap-3 mb-6">
        <input
          v-model="search"
          type="search"
          placeholder="搜尋模板..."
          class="flex-1 min-w-[200px] px-3 py-2 rounded border border-bd bg-surface-raised"
        />
        <select
          v-model="category"
          class="px-3 py-2 rounded border border-bd bg-surface-raised"
        >
          <option :value="null">全部分類</option>
          <option v-for="c in categories" :key="c.category" :value="c.category">
            {{ c.category }} ({{ c.count }})
          </option>
        </select>
        <select
          v-model="sort"
          class="px-3 py-2 rounded border border-bd bg-surface-raised"
        >
          <option value="popular">最熱門</option>
          <option value="recent">最新</option>
          <option value="rating">最高評分</option>
        </select>
      </div>

      <div v-if="loading" class="text-center py-12 text-fg-secondary">
        載入中...
      </div>

      <div v-else-if="items.length === 0" class="text-center py-12 text-fg-secondary">
        沒有找到符合的模板
      </div>

      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <article
          v-for="(t, idx) in items"
          :key="t.id"
          class="card-warm fade-up p-4 flex flex-col cursor-pointer"
          :style="`animation-delay: ${idx * 40}ms`"
          @click="goDetail(t.id)"
        >
          <div
            v-if="t.cover_image_url"
            class="aspect-video rounded bg-neutral-200 mb-3 overflow-hidden"
          >
            <img :src="t.cover_image_url" :alt="t.name" class="w-full h-full object-cover" />
          </div>
          <div class="flex items-start gap-2 mb-2">
            <h3 class="font-semibold flex-1">{{ t.name }}</h3>
            <span
              v-if="t.verified"
              class="text-xs px-1.5 py-0.5 rounded bg-brand-50 text-brand-700"
              title="官方驗證"
            >✓ 驗證</span>
          </div>
          <p class="text-sm text-fg-secondary line-clamp-2 mb-3">{{ t.description }}</p>
          <div class="mt-auto flex items-center justify-between text-xs text-fg-secondary">
            <span>{{ t.publisher_name || '—' }}</span>
            <span class="flex items-center gap-2">
              <span class="text-warning-600" :title="`${t.rating_avg ?? '—'} (${t.rating_count})`">
                {{ ratingStars(t.rating_avg) }}
              </span>
              <span>· {{ t.install_count }} installs</span>
            </span>
          </div>
        </article>
      </div>

      <nav v-if="totalPages > 1" class="flex justify-center items-center gap-3 mt-8">
        <button
          class="px-3 py-1 rounded border border-bd disabled:opacity-50"
          :disabled="page <= 1"
          @click="page--; load()"
        >上一頁</button>
        <span class="text-sm text-fg-secondary">{{ page }} / {{ totalPages }}</span>
        <button
          class="px-3 py-1 rounded border border-bd disabled:opacity-50"
          :disabled="page >= totalPages"
          @click="page++; load()"
        >下一頁</button>
      </nav>
    </section>
  </div>
</template>
