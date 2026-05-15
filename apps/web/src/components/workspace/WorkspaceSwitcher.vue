<template>
  <div ref="rootRef" class="relative">
    <!-- 觸發按鈕 -->
    <button
      @click="open = !open"
      class="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 transition-colors group"
      :title="ws?.name"
    >
      <div
        class="w-7 h-7 rounded-md flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
        :style="{ background: avatarBg }"
      >
        {{ avatarLetters }}
      </div>
      <div class="flex-1 min-w-0 text-left">
        <p class="text-sm font-semibold text-gray-900 truncate">
          {{ ws?.name || '未選擇工作區' }}
        </p>
        <p class="text-[11px] text-gray-400 flex items-center gap-1">
          <span :class="roleDotClass" class="w-1.5 h-1.5 rounded-full"></span>
          <span>{{ roleLabel }}</span>
          <span v-if="ws" class="text-gray-300">·</span>
          <span v-if="ws">{{ ws.member_count }} 人</span>
        </p>
      </div>
      <svg class="w-4 h-4 text-gray-400 group-hover:text-gray-600 flex-shrink-0 transition-transform"
           :class="{ 'rotate-180': open }"
           fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/>
      </svg>
    </button>

    <!-- 下拉選單 -->
    <transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0 -translate-y-1"
      leave-active-class="transition duration-100 ease-in"
      leave-to-class="opacity-0 -translate-y-1"
    >
      <div v-if="open"
           class="absolute z-30 left-0 right-0 mt-1 bg-white rounded-xl border border-gray-200 shadow-lg overflow-hidden">
        <div class="px-3 py-2 border-b border-gray-100">
          <p class="text-[10px] font-semibold text-gray-400 uppercase tracking-wide">您的工作區</p>
        </div>
        <ul class="max-h-72 overflow-y-auto py-1">
          <li v-for="w in store.workspaces" :key="w.id">
            <button
              @click="onPick(w.id)"
              class="w-full flex items-center gap-2.5 px-3 py-2 text-left hover:bg-indigo-50 transition-colors"
              :class="w.id === store.currentId ? 'bg-indigo-50/50' : ''"
            >
              <div
                class="w-6 h-6 rounded flex items-center justify-center text-white text-[10px] font-bold flex-shrink-0"
                :style="{ background: avatarBgFor(w) }"
              >
                {{ initialsOf(w.name) }}
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-gray-900 truncate">{{ w.name }}</p>
                <p class="text-[10px] text-gray-400">{{ roleLabelOf(w.role) }} · {{ w.member_count }} 人</p>
              </div>
              <svg v-if="w.id === store.currentId" class="w-4 h-4 text-indigo-600 flex-shrink-0"
                   fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
              </svg>
            </button>
          </li>
        </ul>
        <div class="px-1 py-1 border-t border-gray-100">
          <button
            @click="onCreate"
            class="w-full flex items-center gap-2 px-3 py-2 text-sm text-indigo-700 hover:bg-indigo-50 rounded-lg transition-colors"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
            </svg>
            建立新工作區
          </button>
        </div>
      </div>
    </transition>

    <!-- 建立 modal -->
    <CreateWorkspaceModal
      v-model:open="showCreate"
      @created="onCreated"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { onClickOutside } from '@vueuse/core'

import type { Workspace } from '../../api/workspace'
import { useWorkspaceStore } from '../../stores/workspace'
import CreateWorkspaceModal from './CreateWorkspaceModal.vue'

const store = useWorkspaceStore()
const open = ref(false)
const showCreate = ref(false)
const rootRef = ref<HTMLElement | null>(null)

onClickOutside(rootRef, () => { open.value = false })

const ws = computed(() => store.current)

const avatarLetters = computed(() => initialsOf(ws.value?.name))
const avatarBg = computed(() => ws.value ? avatarBgFor(ws.value) : '#6b7280')

const roleLabel = computed(() => roleLabelOf(ws.value?.role))
const roleDotClass = computed(() => {
  switch (ws.value?.role) {
    case 'owner':  return 'bg-amber-500'
    case 'admin':  return 'bg-rose-500'
    case 'editor': return 'bg-emerald-500'
    case 'viewer': return 'bg-blue-400'
    default:       return 'bg-gray-300'
  }
})

function roleLabelOf(role: Workspace['role']) {
  return { owner: '擁有者', admin: '管理員', editor: '編輯者', viewer: '檢視者' }[role || 'viewer'] ?? '—'
}

function initialsOf(name?: string | null): string {
  if (!name) return '?'
  const trimmed = name.trim()
  // 中文：取前 2 字；英文：取大寫首字母
  if (/[一-鿿]/.test(trimmed)) return trimmed.slice(0, 2)
  const parts = trimmed.split(/\s+/).filter(Boolean)
  return parts.length >= 2
    ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
    : trimmed.slice(0, 2).toUpperCase()
}

function avatarBgFor(w: Workspace): string {
  // 用 id 派生穩定漸層
  let hash = 0
  for (let i = 0; i < w.id.length; i++) hash = (hash << 5) - hash + w.id.charCodeAt(i)
  const hue = Math.abs(hash) % 360
  return `linear-gradient(135deg, hsl(${hue},65%,55%), hsl(${(hue + 40) % 360},65%,45%))`
}

function onPick(id: string) {
  if (id === store.currentId) {
    open.value = false
    return
  }
  store.switchTo(id)
  open.value = false
  // 簡單做法：reload 頁面，所有 store / fetch 重來
  setTimeout(() => location.reload(), 100)
}

function onCreate() {
  open.value = false
  showCreate.value = true
}

function onCreated() {
  // 切換到新建的 workspace 後 reload
  setTimeout(() => location.reload(), 100)
}

onMounted(async () => {
  if (store.workspaces.length === 0) await store.load()
})
</script>
