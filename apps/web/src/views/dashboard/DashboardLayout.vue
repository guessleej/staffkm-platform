<template>
  <div class="flex flex-col h-screen bg-surface-base text-neutral-900 overflow-hidden">

    <!-- ════════════════════════════════════════
         頂部導覽列：Brand · 主導覽（置中）· 工具
    ════════════════════════════════════════ -->
    <header
      class="h-[72px] px-7 flex items-center gap-6 bg-surface-raised border-b border-neutral-200 sticky top-0 z-20"
    >
      <!-- 左：品牌（v5.7.1：再放大一級，貼齊 modern SaaS 標準） -->
      <router-link to="/" class="flex items-center gap-3.5 flex-shrink-0 mr-3 group">
        <div class="transition-transform duration-200 group-hover:scale-105">
          <BrandLogo :size="52" />
        </div>
        <div class="hidden sm:block min-w-0 leading-tight">
          <p class="font-bold text-neutral-900 text-[1.25rem] tracking-[-0.02em]">staffKM</p>
          <p class="text-xs text-neutral-500 tracking-[0.12em] uppercase mt-1 font-medium">內部知識平台</p>
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

        <!-- 工具（popover grid，替代 v3.x 一字排開的 7 個 icon-only）-->
        <span class="mx-2 w-px h-5 bg-neutral-200" aria-hidden="true"></span>
        <NavMenuPopover
          :label="$t('nav.toolsMenu') || '工具'"
          icon="settings"
          :groups="toolsGroups"
        />

        <!-- Admin（popover grid，替代 v3-v5 累積 14 個 admin link）-->
        <template v-if="auth.hasRole(['admin'])">
          <span class="mx-2 w-px h-5 bg-neutral-200"></span>
          <NavMenuPopover
            label="管理"
            icon="lock"
            :groups="adminGroups"
          />
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
              {{ formatUserName(auth.user) }}
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
                  {{ formatUserName(auth.user) }}
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
    <main ref="mainEl" class="flex-1 overflow-y-auto bg-surface-base">
      <!--
        刻意不用 transition mode="out-in"：連點不同 nav 會卡 leave/enter 競態。
        也不加 :key="$route.fullPath"：不同路由本來就用不同元件，
        強制 remount 反而讓連點時每次都重跑 load() + 暫時 unmount → 視覺空白。
        Sprint 19.x：改用 watch $route.path 觸發 scroll-top + 一次性 fade-in，
        無 transition mode 不會 race，純視覺反饋。
      -->
      <div :class="['page-fade-wrap', pageFadeKey, 'h-full']">
        <router-view />
      </div>
    </main>
  </div>

  <!-- v2.3-A：first-run onboarding wizard -->
  <OnboardingWizard ref="onboardingRef" />
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { onClickOutside } from '@vueuse/core'

import BrandLogo from '../../components/common/BrandLogo.vue'
import HNavItem from '../../components/common/HNavItem.vue'
import NavIconLink from '../../components/common/NavIconLink.vue'
import NavMenuPopover from '../../components/common/NavMenuPopover.vue'
import OnboardingWizard from '../../components/onboarding/OnboardingWizard.vue'
import WorkspaceSwitcher from '../../components/workspace/WorkspaceSwitcher.vue'
import ProjectPicker from '../../components/project/ProjectPicker.vue'
import {
  IconChat, IconApps, IconKnowledge, IconAgent,
  IconUsers, IconCpu, IconSettings,
} from '../../components/icons'

import { useAuthStore } from '../../stores/auth'
import { formatUserName } from '../../utils/userName'
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

// nav active 偵測由各 NavIconLink 自己處理，這裡不再需要 advancedOpen state

// v5.0.4：工具 + 管理 popover 分組（取代 v3.x 一字排開的 24 個 nav item）
const toolsGroups = [
  {
    label: '工作流元件',
    items: [
      { to: '/skills',       label: 'Skills',       icon: 'key',      desc: '能力包' },
      { to: '/tools',        label: 'Tools',        icon: 'settings', desc: '可呼叫工具' },
      { to: '/data-sources', label: '資料來源',     icon: 'database', desc: 'KB / 外部資料' },
      { to: '/mcp/servers',  label: 'MCP Servers',  icon: 'share-2',  desc: 'Model Context Protocol' },
    ],
  },
  {
    label: '自動化 / 用量',
    items: [
      { to: '/triggers', label: '排程觸發', icon: 'refresh',   desc: 'cron / event 觸發' },
      { to: '/memories', label: '長期記憶', icon: 'info',      desc: 'per-user memory' },
      { to: '/usage',    label: '當月用量', icon: 'file-text', desc: 'token / cost' },
    ],
  },
]

const adminGroups = [
  {
    label: '帳號 / 系統',
    items: [
      { to: '/admin/users',  label: '使用者管理', icon: 'user',     desc: '邀請 / 角色 / 停用' },
      { to: '/admin/models', label: '模型供應商', icon: 'database', desc: 'LLM / Embedding / Reranker' },
      { to: '/admin/system', label: '系統設定',   icon: 'settings', desc: '全域偏好' },
    ],
  },
  {
    label: '配額 / 計費',
    items: [
      { to: '/admin/quotas',         label: 'Workspace 配額', icon: 'lock',          desc: '月 cap 設定' },
      { to: '/admin/user-quotas',    label: '使用者配額',     icon: 'user',          desc: 'per-user cap' },
      { to: '/admin/quota-alerts',   label: '配額告警',       icon: 'alert-circle',  desc: 'webhook / slack / email' },
      { to: '/admin/billing',        label: '用戶報表',       icon: 'file-text',     desc: '每月匯出 CSV' },
      { to: '/admin/billing/stripe', label: 'Stripe Billing', icon: 'key',           desc: '訂閱 / 額度 / 發票' },
    ],
  },
  {
    label: '觀測 / 流程',
    items: [
      { to: '/admin/audit-logs',     label: 'Audit Log',     icon: 'file-text',    desc: '操作紀錄' },
      { to: '/admin/run-history',    label: '執行紀錄',      icon: 'play',         desc: 'workflow run + steps' },
      { to: '/admin/approvals',      label: '人工核可',      icon: 'check-circle', desc: '暫停的 workflow' },
      { to: '/admin/webhook-outbox', label: 'Webhook Outbox', icon: 'send',        desc: '失敗重送 / DLQ' },
      { to: '/admin/heartbeats',     label: 'Worker 心跳',   icon: 'loader',       desc: '背景 task 健康' },
      { to: '/admin/slow-queries',   label: '慢查詢分析',    icon: 'database',     desc: 'SQL plan' },
    ],
  },
  {
    label: '基礎建設',
    items: [
      { to: '/admin/regions', label: 'Multi-Region', icon: 'globe', desc: 'active-active scaffolding' },
    ],
  },
]

// Sprint 19.x：route 切換 scroll-top + 視覺 fade，無 mode='out-in' 不會 race
const _route = useRoute()
const mainEl = ref<HTMLElement | null>(null)
const pageFadeKey = ref('a')
watch(() => _route.path, () => {
  // scroll-top
  if (mainEl.value) mainEl.value.scrollTop = 0
  // toggle key 重觸發 CSS animation
  pageFadeKey.value = pageFadeKey.value === 'a' ? 'b' : 'a'
})

const initials = computed(() => {
  const name = formatUserName(auth.user) || '?'
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
