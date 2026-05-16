<template>
  <div class="flex h-screen bg-surface-base text-neutral-900 overflow-hidden">
    <!-- 左側對話歷史抽屜 -->
    <ChatHistoryDrawer
      :conversations="convStore.conversations"
      :active-id="activeConvId"
      :collapsed="drawerCollapsed"
      @toggle="toggleDrawer"
      @new-chat="onNewChat"
      @select="onSelect"
    />

    <!-- 主內容區（router-view 注入 ChatView） -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- 極簡頂部：左 model 顯示、右 user/theme -->
      <header
        class="h-12 px-4 flex items-center justify-between border-b border-neutral-100 flex-shrink-0"
      >
        <!-- 中央顯示：Project picker + model -->
        <div class="flex items-center gap-3 min-w-0">
          <ProjectPicker />
          <span class="w-px h-5 bg-neutral-200"></span>
          <span class="text-xs uppercase tracking-widest text-neutral-400">模型</span>
          <span class="text-sm font-mono text-neutral-700 truncate">gemma4:e4b</span>
        </div>

        <!-- 右側控制 -->
        <div class="flex items-center gap-1">
          <!-- Locale switcher -->
          <select
            :value="$i18n.locale"
            @change="onLocaleChange(($event.target as HTMLSelectElement).value)"
            class="h-8 px-2 text-xs rounded-md border border-neutral-200 bg-transparent text-neutral-600 hover:bg-neutral-100 transition focus:outline-none focus:ring-1 focus:ring-brand-400"
          >
            <option v-for="l in SUPPORTED_LOCALES" :key="l.code" :value="l.code">
              {{ l.label }}
            </option>
          </select>

          <button
            @click="ui.toggleTheme()"
            class="w-9 h-9 flex items-center justify-center rounded-lg text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900 transition"
            :title="ui.isDark ? $t('theme.light') : $t('theme.dark')"
          >
            <svg v-if="!ui.isDark" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>
            </svg>
            <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="4" />
              <path stroke-linecap="round" d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41m11.32-11.32l1.41-1.41" />
            </svg>
          </button>

          <div ref="menuRef" class="relative">
            <button
              @click="userMenuOpen = !userMenuOpen"
              class="flex items-center gap-2 pl-1 pr-2 py-1 rounded-lg hover:bg-neutral-100 transition"
            >
              <div class="w-7 h-7 rounded-full bg-gradient-to-br from-brand-500 to-brand-700 text-white flex items-center justify-center text-xs font-semibold">
                {{ initials }}
              </div>
            </button>
            <transition
              enter-active-class="transition duration-150 ease-out"
              enter-from-class="opacity-0 -translate-y-1"
              leave-active-class="transition duration-100 ease-in"
              leave-to-class="opacity-0 -translate-y-1"
            >
              <div v-if="userMenuOpen"
                   class="absolute right-0 mt-1.5 w-56 bg-surface-raised rounded-xl border border-neutral-200 shadow-lg overflow-hidden z-50">
                <div class="px-4 py-3 border-b border-neutral-100">
                  <p class="text-sm font-semibold text-neutral-900 truncate">
                    {{ auth.user?.display_name || auth.user?.username }}
                  </p>
                  <p class="text-xs text-neutral-500 truncate">
                    {{ auth.user?.email || '' }}
                  </p>
                </div>
                <div class="p-1">
                  <button
                    @click="onLogout"
                    class="w-full flex items-center gap-2 px-3 py-2 text-sm text-rose-600 hover:bg-rose-50 rounded-lg transition"
                  >登出</button>
                </div>
              </div>
            </transition>
          </div>
        </div>
      </header>

      <!-- 主對話內容 -->
      <main class="flex-1 overflow-hidden">
        <router-view />
      </main>
    </div>

    <!-- 右側 Artifact 預覽欄（store.isOpen 控制 slide-in）-->
    <ArtifactPane />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { onClickOutside } from '@vueuse/core'

import ChatHistoryDrawer from '../../components/chat/ChatHistoryDrawer.vue'
import ArtifactPane from '../../components/chat/ArtifactPane.vue'
import ProjectPicker from '../../components/project/ProjectPicker.vue'
import { SUPPORTED_LOCALES, setLocale, type Locale } from '../../i18n'
import { useAuthStore } from '../../stores/auth'
import { useUIStore } from '../../stores/ui'
import { useConversationStore } from '../../stores/conversation'
import { useWorkspaceStore } from '../../stores/workspace'

const auth = useAuthStore()
const ui = useUIStore()
const convStore = useConversationStore()
const workspace = useWorkspaceStore()
const route = useRoute()
const router = useRouter()

// 從 route.query 推導當前選中對話，避免 ChatLayout 與 ChatView state 不同步
const activeConvId = computed<string | null>(() =>
  (route.query.conv as string) || convStore.currentConversation?.id || null,
)

const drawerCollapsed = ref(localStorage.getItem('staffkm.chat_drawer_collapsed') === '1')
function toggleDrawer() {
  drawerCollapsed.value = !drawerCollapsed.value
  localStorage.setItem('staffkm.chat_drawer_collapsed', drawerCollapsed.value ? '1' : '0')
}

const userMenuOpen = ref(false)
const menuRef = ref<HTMLElement | null>(null)
onClickOutside(menuRef, () => { userMenuOpen.value = false })

const initials = computed(() => {
  const name = auth.user?.display_name || auth.user?.username || '?'
  if (/[一-鿿]/.test(name)) return name.slice(0, 1)
  return name.slice(0, 2).toUpperCase()
})

function onNewChat() {
  router.push({ name: 'chat', query: {} })
}
function onSelect(id: string) {
  const conv = convStore.conversations.find((c) => c.id === id)
  if (conv) convStore.selectConversation(conv)
  router.push({ name: 'chat', query: { conv: id } })
}
async function onLogout() {
  userMenuOpen.value = false
  auth.logout()
  router.push('/login')
}

function onLocaleChange(code: string) {
  setLocale(code as Locale)
}

onMounted(async () => {
  // 同時載入 workspace 與對話列表；workspace 沒選會導致管理頁面 API 全 404
  if (workspace.workspaces.length === 0) await workspace.load()
  convStore.fetchConversations()
})
</script>
