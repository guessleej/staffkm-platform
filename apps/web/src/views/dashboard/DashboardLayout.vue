<template>
  <div class="flex flex-col h-screen bg-surface-base text-neutral-900 overflow-hidden">

    <!-- ════════════════════════════════════════
         頂部導覽列：Brand · 主導覽（置中）· 工具
    ════════════════════════════════════════ -->
    <header
      class="h-14 px-5 flex items-center gap-4 bg-surface-raised border-b border-neutral-200 sticky top-0 z-20"
    >
      <!-- 左：品牌 -->
      <router-link to="/" class="flex items-center gap-2.5 flex-shrink-0 mr-2">
        <div
          class="w-8 h-8 rounded-lg flex items-center justify-center"
          style="background: linear-gradient(135deg, hsl(var(--color-brand-500)), hsl(var(--color-brand-700)))"
        >
          <span class="text-white text-[13px] font-bold tracking-tight">S</span>
        </div>
        <div class="hidden sm:block min-w-0 leading-tight">
          <p class="font-semibold text-neutral-900 text-sm">staffKM</p>
          <p class="text-[10px] text-neutral-400 tracking-wide uppercase">內部知識平台</p>
        </div>
      </router-link>

      <!-- 中：主導覽 -->
      <nav class="flex-1 flex items-center justify-center gap-1 min-w-0 overflow-x-auto">
        <HNavItem to="/chat" :label="$t('nav.chat')">
          <template #icon><IconChat :size="16" /></template>
        </HNavItem>
        <HNavItem to="/applications" :label="$t('nav.apps')">
          <template #icon><IconApps :size="16" /></template>
        </HNavItem>
        <HNavItem to="/knowledge" :label="$t('nav.knowledge')">
          <template #icon><IconKnowledge :size="16" /></template>
        </HNavItem>
        <HNavItem to="/agents" :label="$t('nav.agents')">
          <template #icon><IconAgent :size="16" /></template>
        </HNavItem>

        <!-- 進階模組下拉（RFC-006 backlog：Skills / Tools / Data Sources）-->
        <div ref="advancedRef" class="relative">
          <button
            @click="advancedOpen = !advancedOpen"
            class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-sm font-medium transition-colors"
            :class="isAdvancedActive
              ? 'bg-brand-50 text-brand-700'
              : 'text-fg-secondary hover:bg-neutral-100 hover:text-fg'"
          >
            <span>{{ $t('nav.advanced') }}</span>
            <SIcon name="chevron-down" :size="14" :class="advancedOpen ? 'rotate-180' : ''" class="transition-transform" />
          </button>
          <transition
            enter-active-class="transition duration-150 ease-out"
            enter-from-class="opacity-0 translate-y-1"
            leave-active-class="transition duration-100 ease-in"
            leave-to-class="opacity-0 translate-y-1"
          >
            <div
              v-if="advancedOpen"
              class="absolute top-full left-0 mt-1 w-56 bg-surface-raised border border-neutral-200 rounded-xl shadow-lg py-1.5 z-40"
              @click="advancedOpen = false"
            >
              <router-link to="/skills" class="flex items-center gap-2.5 px-3 py-2 text-sm text-fg-secondary hover:bg-neutral-50 hover:text-fg transition">
                <SIcon name="key" :size="14" class="text-fg-tertiary" />
                <div class="flex-1 min-w-0">
                  <div class="font-medium">{{ $t('nav.skills') }}</div>
                  <div class="text-[11px] text-fg-tertiary">可重用 prompt 技能</div>
                </div>
              </router-link>
              <router-link to="/tools" class="flex items-center gap-2.5 px-3 py-2 text-sm text-fg-secondary hover:bg-neutral-50 hover:text-fg transition">
                <SIcon name="settings" :size="14" class="text-fg-tertiary" />
                <div class="flex-1 min-w-0">
                  <div class="font-medium">{{ $t('nav.tools') }}</div>
                  <div class="text-[11px] text-fg-tertiary">工作流可用工具</div>
                </div>
              </router-link>
              <router-link to="/data-sources" class="flex items-center gap-2.5 px-3 py-2 text-sm text-fg-secondary hover:bg-neutral-50 hover:text-fg transition">
                <SIcon name="database" :size="14" class="text-fg-tertiary" />
                <div class="flex-1 min-w-0">
                  <div class="font-medium">{{ $t('nav.dataSources') }}</div>
                  <div class="text-[11px] text-fg-tertiary">外部資料連接器</div>
                </div>
              </router-link>
              <router-link to="/mcp/servers" class="flex items-center gap-2.5 px-3 py-2 text-sm text-fg-secondary hover:bg-neutral-50 hover:text-fg transition">
                <SIcon name="share-2" :size="14" class="text-fg-tertiary" />
                <div class="flex-1 min-w-0">
                  <div class="font-medium">MCP Servers</div>
                  <div class="text-[11px] text-fg-tertiary">Model Context Protocol 工具</div>
                </div>
              </router-link>
            </div>
          </transition>
        </div>

        <template v-if="auth.hasRole(['admin'])">
          <span class="mx-2 w-px h-5 bg-neutral-200"></span>
          <HNavItem to="/admin/users" :label="$t('nav.users')">
            <template #icon><IconUsers :size="16" /></template>
          </HNavItem>
          <HNavItem to="/admin/models" :label="$t('nav.models')">
            <template #icon><IconCpu :size="16" /></template>
          </HNavItem>
          <HNavItem to="/admin/system" :label="$t('nav.settings')">
            <template #icon><IconSettings :size="16" /></template>
          </HNavItem>
        </template>
      </nav>

      <!-- 右：Workspace · Theme · 使用者 -->
      <div class="flex items-center gap-2 flex-shrink-0">
        <div class="hidden md:block w-[200px]">
          <WorkspaceSwitcher />
        </div>

        <!-- Sprint 19-A：Project picker（與 ChatLayout 同步入口）-->
        <div class="hidden md:block">
          <ProjectPicker />
        </div>

        <button
          @click="ui.toggleTheme()"
          class="p-1.5 rounded-lg text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900 transition-colors"
          :title="ui.isDark ? '切換到淺色模式' : '切換到深色模式'"
        >
          <SIcon :name="ui.isDark ? 'sun' : 'moon'" :size="16" />
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
            <span class="text-sm text-neutral-700 hidden lg:inline truncate max-w-[120px]">
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
                  v-if="auth.hasRole(['admin'])"
                  to="/admin/usage"
                  class="flex items-center gap-2 px-3 py-2 text-sm text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
                  @click="open = false"
                >
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M3 3v18h18M7 13l3-3 4 4 5-7"/>
                  </svg>
                  Token 用量
                </router-link>
                <router-link
                  v-if="auth.hasRole(['admin'])"
                  to="/admin/system"
                  class="flex items-center gap-2 px-3 py-2 text-sm text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
                  @click="open = false"
                >
                  <IconSettings :size="16" />
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
      </div>
    </header>

    <!-- ════════════════════════════════════════
         主內容
    ════════════════════════════════════════ -->
    <main class="flex-1 overflow-y-auto bg-surface-base">
      <!--
        刻意不用 transition mode="out-in"：連點不同 nav 會卡 leave/enter 競態。
        也不加 :key="$route.fullPath"：不同路由本來就用不同元件，
        強制 remount 反而讓連點時每次都重跑 load() + 暫時 unmount → 視覺空白。
      -->
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { onClickOutside } from '@vueuse/core'

import HNavItem from '../../components/common/HNavItem.vue'
import WorkspaceSwitcher from '../../components/workspace/WorkspaceSwitcher.vue'
import ProjectPicker from '../../components/project/ProjectPicker.vue'
import {
  IconChat, IconApps, IconKnowledge, IconAgent,
  IconUsers, IconCpu, IconSettings,
} from '../../components/icons'

import { useAuthStore } from '../../stores/auth'
import { useProjectStore } from '../../stores/project'
import { useUIStore } from '../../stores/ui'
import { useWorkspaceStore } from '../../stores/workspace'
import { SIcon } from '@staffkm/ui-kit'

const auth = useAuthStore()
const ui = useUIStore()
const workspace = useWorkspaceStore()
const projects = useProjectStore()
const router = useRouter()

const open = ref(false)
const menuRef = ref<HTMLElement | null>(null)
onClickOutside(menuRef, () => { open.value = false })

// 進階模組下拉
const advancedOpen = ref(false)
const advancedRef = ref<HTMLElement | null>(null)
onClickOutside(advancedRef, () => { advancedOpen.value = false })
const route = useRoute()
const isAdvancedActive = computed(() =>
  ['/skills', '/tools', '/data-sources', '/mcp'].some(p => route.path.startsWith(p))
)

const initials = computed(() => {
  const name = auth.user?.display_name || auth.user?.username || '?'
  if (/[一-鿿]/.test(name)) return name.slice(0, 1)
  return name.slice(0, 2).toUpperCase()
})

async function onLogout() {
  open.value = false
  auth.logout()
  router.push('/login')
}

onMounted(async () => {
  if (workspace.workspaces.length === 0) await workspace.load()
  // D-6：載入 projects 讓「目前 Project」過濾在管理頁面也能用
  projects.load()
})
</script>
