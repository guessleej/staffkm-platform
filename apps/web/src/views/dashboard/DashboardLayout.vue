<template>
  <div class="flex h-screen bg-surface-base text-neutral-900 overflow-hidden">

    <!-- ════════════════════════════════════════
         側欄
    ════════════════════════════════════════ -->
    <aside
      class="bg-surface-raised border-r border-neutral-200 flex flex-col flex-shrink-0 transition-[width] duration-300 ease-out"
      :class="ui.sidebarCollapsed ? 'w-[64px]' : 'w-[240px]'"
    >
      <!-- Brand -->
      <div class="h-14 flex items-center border-b border-neutral-200 flex-shrink-0"
           :class="ui.sidebarCollapsed ? 'justify-center px-3' : 'px-4 gap-2.5'">
        <div class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
             style="background: linear-gradient(135deg, hsl(var(--color-brand-500)), hsl(var(--color-brand-700)))">
          <span class="text-white text-[13px] font-bold tracking-tight">S</span>
        </div>
        <div v-if="!ui.sidebarCollapsed" class="min-w-0">
          <p class="font-semibold text-neutral-900 text-sm leading-tight">staffKM</p>
          <p class="text-[10px] text-neutral-400 leading-tight tracking-wide uppercase">內部知識平台</p>
        </div>
      </div>

      <!-- Workspace Switcher（折疊時隱藏） -->
      <div v-if="!ui.sidebarCollapsed" class="p-2.5 border-b border-neutral-100">
        <WorkspaceSwitcher />
      </div>

      <!-- 主導覽 -->
      <nav class="flex-1 overflow-y-auto py-3"
           :class="ui.sidebarCollapsed ? 'px-2 space-y-1' : 'px-2.5 space-y-0.5'">
        <p v-if="!ui.sidebarCollapsed" class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider px-3 pb-2">
          工作區
        </p>
        <NavItem to="/chat" label="對話" :collapsed="ui.sidebarCollapsed">
          <template #icon><IconChat :size="16" /></template>
        </NavItem>
        <NavItem to="/applications" label="應用" :collapsed="ui.sidebarCollapsed">
          <template #icon><IconApps :size="16" /></template>
        </NavItem>
        <NavItem to="/knowledge" label="知識庫" :collapsed="ui.sidebarCollapsed">
          <template #icon><IconKnowledge :size="16" /></template>
        </NavItem>
        <NavItem to="/agents" label="代理人" :collapsed="ui.sidebarCollapsed">
          <template #icon><IconAgent :size="16" /></template>
        </NavItem>

        <template v-if="auth.hasRole(['admin'])">
          <div v-if="!ui.sidebarCollapsed" class="pt-4 mt-3 border-t border-neutral-100">
            <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider px-3 pb-2">系統管理</p>
          </div>
          <div v-else class="my-3 mx-3 border-t border-neutral-100"></div>
          <NavItem to="/admin/users" label="使用者" :collapsed="ui.sidebarCollapsed">
            <template #icon><IconUsers :size="16" /></template>
          </NavItem>
          <NavItem to="/admin/models" label="模型" :collapsed="ui.sidebarCollapsed">
            <template #icon><IconCpu :size="16" /></template>
          </NavItem>
          <NavItem to="/admin/system" label="設定" :collapsed="ui.sidebarCollapsed">
            <template #icon><IconSettings :size="16" /></template>
          </NavItem>
        </template>
      </nav>

      <!-- 折疊狀態的展開按鈕 -->
      <div v-if="ui.sidebarCollapsed" class="px-2 py-2 border-t border-neutral-100">
        <button
          @click="ui.toggleSidebar()"
          title="展開側欄"
          class="w-full h-9 flex items-center justify-center rounded-lg text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700 transition-colors"
        >
          <IconChevronRight :size="16" />
        </button>
      </div>
    </aside>

    <!-- ════════════════════════════════════════
         主內容
    ════════════════════════════════════════ -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <AppTopbar />
      <main class="flex-1 overflow-y-auto bg-surface-base">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'

import AppTopbar from '../../components/common/AppTopbar.vue'
import NavItem from '../../components/common/NavItem.vue'
import WorkspaceSwitcher from '../../components/workspace/WorkspaceSwitcher.vue'
import {
  IconChat, IconApps, IconKnowledge, IconAgent,
  IconUsers, IconCpu, IconSettings, IconChevronRight,
} from '../../components/icons'

import { useAuthStore } from '../../stores/auth'
import { useUIStore } from '../../stores/ui'
import { useWorkspaceStore } from '../../stores/workspace'

const auth = useAuthStore()
const ui = useUIStore()
const workspace = useWorkspaceStore()

onMounted(() => {
  if (workspace.workspaces.length === 0) workspace.load()
})
</script>
