<template>
  <ul class="space-y-0.5 select-none">
    <li v-for="node in nodes" :key="node.id">
      <div
        class="group flex items-center gap-1 px-2 py-1.5 rounded-md text-sm cursor-pointer transition-colors"
        :class="activeId === node.id
          ? 'bg-neutral-100 text-neutral-900'
          : 'text-neutral-700 hover:bg-neutral-50 hover:text-neutral-900'"
        :style="{ paddingLeft: `${depth * 12 + 8}px` }"
        @click="onClick(node)"
      >
        <!-- 展開／收合 chevron（無 children 時保留同寬，避免標題對不齊）-->
        <button
          v-if="hasChildren(node)"
          @click.stop="toggle(node.id)"
          class="w-4 h-4 flex items-center justify-center text-neutral-400 hover:text-neutral-700 transition"
        >
          <svg
            class="w-3 h-3 transition-transform"
            :class="expanded.has(node.id) ? 'rotate-90' : ''"
            fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
          </svg>
        </button>
        <span v-else class="w-4 h-4 flex-shrink-0"></span>

        <!-- folder icon -->
        <svg class="w-3.5 h-3.5 flex-shrink-0 text-neutral-400" fill="currentColor" viewBox="0 0 24 24">
          <path d="M10 4H4a2 2 0 00-2 2v12a2 2 0 002 2h16a2 2 0 002-2V8a2 2 0 00-2-2h-8l-2-2z"/>
        </svg>

        <span class="truncate flex-1">{{ node.name }}</span>

        <!-- 計數徽章 -->
        <span
          v-if="typeof node.count === 'number'"
          class="text-[10px] text-neutral-400 group-hover:text-neutral-500"
        >{{ node.count }}</span>
      </div>

      <!-- 遞迴子樹 -->
      <FolderTree
        v-if="hasChildren(node) && expanded.has(node.id)"
        :nodes="node.children!"
        :active-id="activeId"
        :depth="depth + 1"
        @select="(n) => $emit('select', n)"
      />
    </li>
  </ul>
</template>

<script setup lang="ts">
import { ref } from 'vue'

export interface FolderNode {
  id: string
  name: string
  count?: number
  children?: FolderNode[]
}

const props = withDefaults(
  defineProps<{
    nodes: FolderNode[]
    activeId?: string | null
    depth?: number
  }>(),
  { depth: 0, activeId: null },
)

const emit = defineEmits<{ (e: 'select', node: FolderNode): void }>()

// 展開狀態（每個 FolderTree 實例獨立）
const expanded = ref<Set<string>>(new Set())

function hasChildren(n: FolderNode): boolean {
  return !!n.children && n.children.length > 0
}

function toggle(id: string) {
  const s = new Set(expanded.value)
  if (s.has(id)) s.delete(id)
  else           s.add(id)
  expanded.value = s
}

function onClick(node: FolderNode) {
  emit('select', node)
}
</script>
