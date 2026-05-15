<template>
  <header class="h-14 px-5 flex items-center gap-4 bg-surface-raised border-b border-neutral-200 sticky top-0 z-20">
    <!-- 折疊側欄 -->
    <button
      @click="ui.toggleSidebar()"
      class="-ml-1.5 p-1.5 rounded-lg text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900 transition-colors"
      :title="ui.sidebarCollapsed ? '展開側欄' : '折疊側欄'"
    >
      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round"
              :d="ui.sidebarCollapsed
                  ? 'M4 6h16M4 12h10M4 18h16'
                  : 'M4 6h16M4 12h16M4 18h16'"/>
      </svg>
    </button>

    <!-- 麵包屑 -->
    <nav class="flex-1 flex items-center gap-1.5 text-sm min-w-0 overflow-hidden">
      <template v-for="(c, i) in crumbs" :key="i">
        <span v-if="i > 0" class="text-neutral-300">/</span>
        <router-link
          v-if="c.to && i < crumbs.length - 1"
          :to="c.to"
          class="text-neutral-500 hover:text-neutral-900 transition-colors truncate"
        >{{ c.label }}</router-link>
        <span v-else class="text-neutral-900 font-medium truncate">{{ c.label }}</span>
      </template>
    </nav>

    <!-- 動作區（slot） -->
    <div class="flex items-center gap-1.5">
      <slot name="actions" />
    </div>

    <!-- 分隔線 -->
    <div class="w-px h-5 bg-neutral-200"></div>

    <!-- Theme toggle -->
    <button
      @click="ui.toggleTheme()"
      class="p-1.5 rounded-lg text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900 transition-colors"
      :title="ui.isDark ? '切換到淺色模式' : '切換到深色模式'"
    >
      <svg v-if="!ui.isDark" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>
      </svg>
      <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="4" />
        <path stroke-linecap="round" d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41m11.32-11.32l1.41-1.41" />
      </svg>
    </button>

    <!-- 使用者選單 -->
    <div ref="menuRef" class="relative">
      <button
        @click="open = !open"
        class="flex items-center gap-2 pl-2 pr-1 py-1 rounded-lg hover:bg-neutral-100 transition-colors"
      >
        <div class="w-7 h-7 rounded-full bg-gradient-to-br from-brand-500 to-brand-700 text-white flex items-center justify-center text-xs font-semibold flex-shrink-0">
          {{ initials }}
        </div>
        <span class="text-sm text-neutral-700 hidden md:inline truncate max-w-[120px]">
          {{ auth.user?.display_name || auth.user?.username || '—' }}
        </span>
        <svg class="w-3.5 h-3.5 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/>
        </svg>
      </button>

      <transition
        enter-active-class="transition duration-150 ease-out"
        enter-from-class="opacity-0 -translate-y-1"
        leave-active-class="transition duration-100 ease-in"
        leave-to-class="opacity-0 -translate-y-1"
      >
        <div v-if="open"
             class="absolute right-0 mt-1.5 w-56 bg-surface-raised rounded-xl border border-neutral-200 shadow-lg overflow-hidden">
          <div class="px-4 py-3 border-b border-neutral-100">
            <p class="text-sm font-semibold text-neutral-900 truncate">
              {{ auth.user?.display_name || auth.user?.username }}
            </p>
            <p class="text-xs text-neutral-500 truncate">
              {{ auth.user?.email || auth.user?.department || '' }}
            </p>
          </div>
          <div class="p-1">
            <router-link
              to="/admin/system"
              v-if="auth.hasRole(['admin'])"
              class="flex items-center gap-2 px-3 py-2 text-sm text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
              @click="open = false"
            >
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
              系統設定
            </router-link>
            <button
              @click="onLogout"
              class="w-full flex items-center gap-2 px-3 py-2 text-sm text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
            >
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
              </svg>
              登出
            </button>
          </div>
        </div>
      </transition>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { onClickOutside } from '@vueuse/core'

import { useAuthStore } from '../../stores/auth'
import { useUIStore } from '../../stores/ui'

const ui = useUIStore()
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const open = ref(false)
const menuRef = ref<HTMLElement | null>(null)
onClickOutside(menuRef, () => { open.value = false })

const initials = computed(() => {
  const name = auth.user?.display_name || auth.user?.username || '?'
  if (/[一-鿿]/.test(name)) return name.slice(0, 1)
  return name.slice(0, 2).toUpperCase()
})

// 麵包屑：從 route matched + meta.title 推
const crumbs = computed(() => {
  const items: { label: string; to?: string }[] = [{ label: '首頁', to: '/' }]
  for (const m of route.matched) {
    const t = m.meta?.title
    if (typeof t === 'string' && t) items.push({ label: t, to: m.path })
  }
  return items
})

async function onLogout() {
  open.value = false
  auth.logout()
  router.push('/login')
}
</script>
