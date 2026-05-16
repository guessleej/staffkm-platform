<template>
  <aside
    class="flex flex-col bg-surface-raised border-r border-neutral-200 transition-[width] duration-200 ease-out flex-shrink-0 overflow-hidden"
    :class="collapsed ? 'w-[52px]' : 'w-[260px]'"
  >
    <!-- Brand + Toggle -->
    <div class="h-12 flex items-center px-2 border-b border-neutral-100 gap-1.5">
      <button
        @click="$emit('toggle')"
        class="w-9 h-9 flex items-center justify-center rounded-lg text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900 transition flex-shrink-0"
        :title="collapsed ? '展開對話列表' : '收起對話列表'"
      >
        <IconMenu :size="16" />
      </button>
      <router-link
        v-if="!collapsed"
        to="/"
        class="flex items-center gap-2 min-w-0 hover:opacity-80 transition"
      >
        <div
          class="w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0"
          style="background: linear-gradient(135deg, hsl(var(--color-brand-500)), hsl(var(--color-brand-700)))"
        >
          <span class="text-white text-xs font-bold">S</span>
        </div>
        <span class="font-semibold text-sm text-neutral-900 truncate">staffKM</span>
      </router-link>
    </div>

    <!-- New chat -->
    <div class="px-2 pt-2">
      <button
        @click="$emit('new-chat')"
        class="w-full h-9 flex items-center gap-2 rounded-lg text-sm font-medium transition-colors border border-neutral-200 hover:bg-neutral-50 text-neutral-700"
        :class="collapsed ? 'justify-center px-0' : 'px-3'"
        :title="collapsed ? '新對話' : undefined"
      >
        <IconPlus :size="14" />
        <span v-if="!collapsed">新對話</span>
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
            <button
              @click="$emit('select', c.id)"
              class="w-full text-left px-2.5 py-2 rounded-lg text-sm transition-colors truncate group"
              :class="activeId === c.id
                ? 'bg-neutral-100 text-neutral-900'
                : 'text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900'"
            >
              <span class="block truncate">{{ c.title || '未命名對話' }}</span>
            </button>
          </li>
        </ul>
      </div>
      <p
        v-if="!groups.length"
        class="text-center text-xs text-neutral-400 py-8"
      >尚無對話記錄</p>
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
        :title="collapsed ? link.label : undefined"
      >
        <component :is="link.icon" :size="16" />
        <span v-if="!collapsed">{{ link.label }}</span>
      </router-link>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { groupByDate } from '../../utils/dateGroup'
import {
  IconMenu, IconPlus, IconKnowledge, IconApps, IconAgent, IconSettings,
} from '../icons'

const props = defineProps<{
  conversations: { id: string; title: string; updated_at: string }[]
  activeId?: string | null
  collapsed?: boolean
}>()

defineEmits<{
  (e: 'toggle'): void
  (e: 'new-chat'): void
  (e: 'select', id: string): void
}>()

const groups = computed(() =>
  groupByDate(
    [...props.conversations].sort(
      (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
    ),
    (c) => c.updated_at,
  ),
)

const adminLinks = [
  { to: '/knowledge',    label: '知識庫',   icon: IconKnowledge },
  { to: '/applications', label: '應用',     icon: IconApps },
  { to: '/agents',       label: '代理人',   icon: IconAgent },
  { to: '/admin/system', label: '設定',     icon: IconSettings },
]
</script>
