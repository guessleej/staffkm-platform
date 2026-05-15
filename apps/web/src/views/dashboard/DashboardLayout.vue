<template>
  <div class="flex h-screen bg-gray-50 overflow-hidden">
    <!-- 側邊欄 -->
    <aside class="w-60 bg-white border-r border-gray-200 flex flex-col flex-shrink-0">
      <!-- Logo -->
      <div class="h-16 flex items-center px-5 border-b border-gray-200">
        <div class="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center mr-3">
          <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <div>
          <p class="font-bold text-gray-900 text-sm leading-tight">StaffKM</p>
          <p class="text-xs text-gray-400">行政知識管理</p>
        </div>
      </div>

      <!-- Workspace 切換器 -->
      <div class="p-3 border-b border-gray-100">
        <WorkspaceSwitcher />
      </div>

      <!-- 導覽選單 -->
      <nav class="flex-1 p-3 space-y-1 overflow-y-auto">
        <NavItem to="/chat" icon="💬" label="智慧問答" />
        <NavItem to="/applications" icon="🚀" label="AI 應用" />
        <NavItem to="/knowledge" icon="📚" label="知識庫管理" />
        <NavItem to="/agents" icon="🤖" label="AI 代理人" />

        <div v-if="auth.hasRole(['admin'])" class="pt-3 mt-3 border-t border-gray-100">
          <p class="text-xs font-medium text-gray-400 px-3 pb-2">系統管理</p>
          <NavItem to="/admin/users" icon="👥" label="使用者管理" />
          <NavItem to="/admin/models" icon="🧠" label="模型供應商" />
          <NavItem to="/admin/system" icon="⚙️" label="系統設定" />
        </div>
      </nav>

      <!-- 使用者資訊 -->
      <div class="p-3 border-t border-gray-200">
        <div class="flex items-center gap-3 px-2 py-2">
          <div class="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-700 font-medium text-sm">
            {{ auth.user?.display_name?.charAt(0) || auth.user?.username?.charAt(0) || '?' }}
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-gray-900 truncate">
              {{ auth.user?.display_name || auth.user?.username }}
            </p>
            <p class="text-xs text-gray-400 truncate">{{ auth.user?.department || '' }}</p>
          </div>
          <button @click="handleLogout" title="登出"
            class="text-gray-400 hover:text-red-500 transition">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </button>
        </div>
      </div>
    </aside>

    <!-- 主內容區 -->
    <main class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useWorkspaceStore } from '../../stores/workspace'
import NavItem from '../../components/common/NavItem.vue'
import WorkspaceSwitcher from '../../components/workspace/WorkspaceSwitcher.vue'

const auth = useAuthStore()
const workspace = useWorkspaceStore()
const router = useRouter()

onMounted(() => {
  // 載入使用者所屬的 workspace 清單
  if (workspace.workspaces.length === 0) workspace.load()
})

async function handleLogout() {
  workspace.reset()
  auth.logout()
  router.push('/login')
}
</script>
