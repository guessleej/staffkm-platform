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
        <!-- 中央顯示：Project picker + model / KB override (MaxKB v2.8) -->
        <div class="flex items-center gap-3 min-w-0">
          <ProjectPicker />
          <span class="w-px h-5 bg-neutral-200"></span>
          <!-- Model override -->
          <label class="text-xs uppercase tracking-widest text-neutral-400">模型</label>
          <select
            v-model="chatOverride.model"
            class="h-8 px-2 text-xs rounded-md border border-neutral-200 bg-transparent text-neutral-700 max-w-[180px] focus:outline-none focus:ring-1 focus:ring-brand-400"
            :title="chatOverride.model ? '本對話將以此 model 覆寫預設' : '使用 application 預設 model'"
          >
            <option value="">預設</option>
            <option v-for="m in availableModels" :key="m" :value="m">{{ m }}</option>
          </select>
          <!-- KB override -->
          <span class="w-px h-5 bg-neutral-200"></span>
          <label class="text-xs uppercase tracking-widest text-neutral-400">KB</label>
          <button
            @click="kbPickerOpen = !kbPickerOpen"
            ref="kbPickerBtn"
            class="h-8 px-2 text-xs rounded-md border border-neutral-200 text-neutral-700 hover:bg-neutral-50 transition flex items-center gap-1"
          >
            <span>{{ chatOverride.kb_ids.length ? `已選 ${chatOverride.kb_ids.length}` : '預設' }}</span>
            <SIcon name="chevron-down" :size="12" />
          </button>
          <div v-if="kbPickerOpen" ref="kbPickerPanel" class="absolute top-12 left-[280px] z-50 w-72 bg-surface-raised rounded-lg border border-neutral-200 shadow-lg p-2 max-h-72 overflow-auto">
            <p v-if="!availableKbs.length" class="text-xs text-neutral-500 p-2">尚無可用知識庫</p>
            <label v-for="kb in availableKbs" :key="kb.id" class="flex items-center gap-2 px-2 py-1.5 hover:bg-neutral-50 rounded cursor-pointer text-xs">
              <input
                type="checkbox"
                :value="kb.id"
                :checked="chatOverride.kb_ids.includes(kb.id)"
                @change="toggleKb(kb.id)"
              />
              <span class="truncate">{{ kb.name }}</span>
            </label>
            <div v-if="chatOverride.kb_ids.length" class="border-t border-neutral-100 pt-2 mt-2">
              <button @click="chatOverride.kb_ids = []" class="text-[11px] text-brand-600 hover:underline">清除</button>
            </div>
          </div>
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
            <SIcon :name="ui.isDark ? 'sun' : 'moon'" :size="16" />
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

    <!-- 右側 Artifact 預覽欄（lazy：只有真的要開時才 import marked + highlight.js）-->
    <ArtifactPane v-if="artifact.isOpen" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { onClickOutside } from '@vueuse/core'

import ChatHistoryDrawer from '../../components/chat/ChatHistoryDrawer.vue'
// 19-perf：ArtifactPane 含 marked + highlight.js (~400KB)；只有 store.isOpen 時才
// 真的渲染，用 defineAsyncComponent 讓它在 pane 首次開啟時才下載 md-vendor chunk
import { defineAsyncComponent } from 'vue'
const ArtifactPane = defineAsyncComponent(
  () => import('../../components/chat/ArtifactPane.vue')
)
import ProjectPicker from '../../components/project/ProjectPicker.vue'
import { SUPPORTED_LOCALES, setLocale, type Locale } from '../../i18n'
import { useAuthStore } from '../../stores/auth'
import { useUIStore } from '../../stores/ui'
import { useConversationStore } from '../../stores/conversation'
import { useArtifactStore } from '../../stores/artifact'
import { SIcon } from '@staffkm/ui-kit'
import { useProjectStore } from '../../stores/project'
import { useWorkspaceStore } from '../../stores/workspace'
import { useChatOverrideStore } from '../../stores/chatOverride'
import { http } from '../../api'

const auth = useAuthStore()
const ui = useUIStore()
const convStore = useConversationStore()
const artifact = useArtifactStore()
const workspace = useWorkspaceStore()
const projects = useProjectStore()
const chatOverride = useChatOverrideStore()
const route = useRoute()
const router = useRouter()

// MaxKB v2.8：對話中切 model / KB 用的資料
const availableModels = ref<string[]>([])
const availableKbs = ref<Array<{ id: string; name: string }>>([])
const kbPickerOpen = ref(false)
const kbPickerBtn = ref<HTMLElement | null>(null)
const kbPickerPanel = ref<HTMLElement | null>(null)
onClickOutside(kbPickerPanel, () => { kbPickerOpen.value = false }, { ignore: [kbPickerBtn] })

function toggleKb(id: string) {
  const i = chatOverride.kb_ids.indexOf(id)
  if (i >= 0) chatOverride.kb_ids.splice(i, 1)
  else chatOverride.kb_ids.push(id)
}

async function loadOverrideOptions() {
  // 撈當前 workspace 可用 model 清單
  try {
    const { data } = await http.get('/admin/models')
    const items = data.data?.items ?? data.data ?? []
    availableModels.value = items
      .filter((m: any) => m.is_enabled !== false)
      .map((m: any) => m.model_name || m.name)
      .filter(Boolean)
  } catch { /* admin/models 可能無權限 → 用 application chat 預設 */ }
  // 撈可選 KBs
  try {
    const { data } = await http.get('/knowledge')
    availableKbs.value = (data.data?.items ?? data.data ?? [])
      .map((k: any) => ({ id: k.id, name: k.name }))
  } catch { /* 非關鍵 */ }
}

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
  // workspace 必須先載入，否則後續 project / conversation API 都拿不到資料
  if (workspace.workspaces.length === 0) await workspace.load()
  // 對話列表 + project 列表並行載入
  convStore.fetchConversations()
  projects.load()
  loadOverrideOptions()
})
</script>
