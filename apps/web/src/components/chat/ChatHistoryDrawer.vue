<template>
  <aside
    class="flex flex-col bg-surface-raised border-r border-neutral-200 transition-[width] duration-200 ease-out flex-shrink-0 overflow-hidden"
    :class="collapsed ? 'w-[52px]' : 'w-[260px]'"
  >
    <!-- Brand + Toggle -->
    <div class="h-[60px] flex items-center px-2.5 border-b border-neutral-100 gap-1.5">
      <button
        @click="$emit('toggle')"
        class="w-9 h-9 flex items-center justify-center rounded-lg text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900 transition flex-shrink-0"
        :title="collapsed ? $t('chat.newChat') : ''"
      >
        <IconMenu :size="16" />
      </button>
      <router-link
        v-if="!collapsed"
        to="/"
        class="flex items-center gap-3 min-w-0 hover:opacity-80 transition group"
      >
        <div class="transition-transform duration-200 group-hover:scale-105">
          <BrandLogo :size="42" />
        </div>
        <span class="font-bold text-[1.05rem] text-neutral-900 truncate tracking-[-0.02em]">staffKM</span>
      </router-link>
    </div>

    <!-- New chat -->
    <div class="px-2 pt-2">
      <button
        @click="$emit('new-chat')"
        class="w-full h-9 flex items-center gap-2 rounded-lg text-sm font-medium transition-colors border border-neutral-200 hover:bg-neutral-50 text-neutral-700"
        :class="collapsed ? 'justify-center px-0' : 'px-3'"
        :title="collapsed ? $t('chat.newChat') : undefined"
      >
        <IconPlus :size="14" />
        <span v-if="!collapsed">{{ $t('chat.newChat') }}</span>
      </button>
    </div>

    <!-- Date-grouped conversations -->
    <nav v-if="!collapsed" class="flex-1 overflow-y-auto px-2 py-3 space-y-4">
      <div v-for="group in groups" :key="group.key">
        <p class="px-2 pb-1 text-[10px] font-semibold uppercase tracking-wider text-neutral-400">
          {{ group.label }}
        </p>
        <ul class="space-y-0.5">
          <li v-for="c in group.items" :key="c.id">
            <div
              class="group/row relative flex items-center rounded-lg transition-colors"
              :class="activeId === c.id
                ? 'bg-neutral-100 text-neutral-900'
                : 'text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900'"
            >
              <button
                @click="$emit('select', c.id)"
                class="flex-1 min-w-0 text-left pl-2.5 pr-1 py-2 text-sm truncate"
              >
                <span class="block truncate">{{ c.title || '未命名對話' }}</span>
              </button>
              <button
                @click.stop="confirmDelete(c.id, c.title)"
                class="flex-shrink-0 w-7 h-7 mr-1 flex items-center justify-center rounded-md
                       text-neutral-400 hover:text-rose-600 hover:bg-rose-50 transition
                       opacity-0 group-hover/row:opacity-100 focus:opacity-100"
                :title="`刪除「${c.title || '未命名對話'}」`"
                aria-label="刪除對話"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                     stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="3 6 5 6 21 6"></polyline>
                  <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"></path>
                  <path d="M10 11v6"></path><path d="M14 11v6"></path>
                  <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"></path>
                </svg>
              </button>
            </div>
          </li>
        </ul>
      </div>
      <p
        v-if="!groups.length"
        class="text-center text-xs text-neutral-400 py-8"
      >{{ $t('chat.historyEmpty') }}</p>
    </nav>

    <!-- Collapsed body: empty (only toggle + new-chat visible) -->
    <div v-else class="flex-1" />

    <!-- Bottom bar: navigate to admin areas -->
    <div class="border-t border-neutral-100 p-2 space-y-0.5">
      <router-link
        v-for="link in adminLinks"
        :key="link.to"
        :to="link.to"
        class="flex items-center gap-2 h-9 rounded-lg text-sm text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900 transition-colors"
        :class="collapsed ? 'justify-center' : 'px-2.5'"
        :title="collapsed ? $t(link.key) : undefined"
      >
        <component :is="link.icon" :size="16" />
        <span v-if="!collapsed">{{ $t(link.key) }}</span>
      </router-link>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { groupByDate } from '../../utils/dateGroup'
import BrandLogo from '../common/BrandLogo.vue'
import {
  IconMenu, IconPlus, IconKnowledge, IconApps, IconAgent, IconSettings,
} from '../icons'

const props = defineProps<{
  conversations: { id: string; title: string; updated_at: string }[]
  activeId?: string | null
  collapsed?: boolean
}>()

const emit = defineEmits<{
  (e: 'toggle'): void
  (e: 'new-chat'): void
  (e: 'select', id: string): void
  (e: 'delete', id: string): void
}>()

function confirmDelete(id: string, title: string) {
  const name = title || '未命名對話'
  if (window.confirm(`確定要刪除「${name}」？\n此操作無法復原。`)) {
    emit('delete', id)
  }
}

const groups = computed(() =>
  groupByDate(
    [...props.conversations].sort(
      (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
    ),
    (c) => c.updated_at,
  ),
)

// 順序對齊 DashboardLayout 頂部水平導覽，避免認知混淆
// 用 i18n key 而非 hardcoded 字串，切語系即時更新
const adminLinks = [
  { to: '/applications', key: 'nav.apps',      icon: IconApps },
  { to: '/knowledge',    key: 'nav.knowledge', icon: IconKnowledge },
  { to: '/agents',       key: 'nav.agents',    icon: IconAgent },
  { to: '/admin/system', key: 'nav.settings',  icon: IconSettings },
]
</script>
