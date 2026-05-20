<template>
  <div ref="rootRef" class="relative inline-block">
    <button
      ref="btnRef"
      @click.stop="onToggle"
      class="px-2 text-fg-tertiary hover:text-brand-600 hover:bg-brand-50 rounded-md transition-colors py-1.5"
      :title="alreadyIn ? '已加入某 Project — 點擊管理' : '加入 Project'"
    >
      <SIcon :name="alreadyIn ? 'folder' : 'plus'" :size="14" />
    </button>

    <!-- v5.9.20: Teleport 到 body 避免被 card 的 overflow-hidden 截掉
         配合 fixed positioning 計算 btn rect 定位 -->
    <Teleport to="body">
    <transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0 translate-y-1"
      leave-active-class="transition duration-100 ease-in"
      leave-to-class="opacity-0 translate-y-1"
    >
      <div
        v-if="open"
        ref="popoverRef"
        :style="popoverStyle"
        class="fixed w-56 bg-surface-raised border border-neutral-200 rounded-xl shadow-lg z-50 overflow-hidden"
        @click.stop
      >
        <div class="px-3 py-2 border-b border-neutral-100">
          <p class="text-[11px] text-fg-tertiary">加入 / 移出 Project</p>
        </div>

        <div v-if="!projects.projects.length" class="px-3 py-4 text-center text-xs text-fg-tertiary">
          尚未建立任何 Project
          <router-link to="/projects" class="block mt-2 text-brand-600 hover:underline">→ 去建立</router-link>
        </div>

        <ul v-else class="py-1 max-h-60 overflow-y-auto">
          <li v-for="p in projects.projects" :key="p.id">
            <button
              @click="toggle(p.id)"
              :disabled="busy"
              class="w-full flex items-center gap-2 px-3 py-2 text-left text-sm hover:bg-neutral-50 transition disabled:opacity-50"
            >
              <span class="text-base leading-none">{{ p.emoji || '#' }}</span>
              <span class="flex-1 truncate text-fg">{{ p.name }}</span>
              <SIcon
                v-if="isIn(p.id)"
                name="check"
                :size="14"
                class="text-brand-600 flex-shrink-0"
              />
            </button>
          </li>
        </ul>

        <div class="border-t border-neutral-100 p-1">
          <router-link
            to="/projects"
            @click="open = false"
            class="w-full flex items-center gap-2 px-3 py-2 text-xs text-fg-secondary hover:bg-neutral-100 rounded-lg transition"
          >
            <SIcon name="settings" :size="12" />
            管理 Projects
          </router-link>
        </div>
      </div>
    </transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { onClickOutside } from '@vueuse/core'
import { SIcon } from '@staffkm/ui-kit'
import { useProjectStore } from '../../stores/project'

const props = defineProps<{
  kind: 'kb' | 'app'
  resourceId: string
}>()

const projects = useProjectStore()

const open = ref(false)
const busy = ref(false)
const rootRef = ref<HTMLElement | null>(null)
const btnRef = ref<HTMLButtonElement | null>(null)
const popoverRef = ref<HTMLElement | null>(null)
const popoverStyle = ref<Record<string, string>>({})

// 點按鈕外關閉（含 teleport 後的 popover）
onClickOutside(rootRef, (e) => {
  // 若點到 popover 本體就不關
  if (popoverRef.value && popoverRef.value.contains(e.target as Node)) return
  open.value = false
})

async function onToggle() {
  open.value = !open.value
  if (open.value) {
    await nextTick()
    // 計算 popover 位置：對齊按鈕右邊、下方
    const r = btnRef.value?.getBoundingClientRect()
    if (r) {
      const popoverW = 224 // w-56 = 14rem ≈ 224px
      // 右對齊
      const left = Math.max(8, r.right - popoverW)
      const top = r.bottom + 4
      popoverStyle.value = { left: `${left}px`, top: `${top}px` }
    }
  }
}

const fieldName = computed(() => props.kind === 'kb' ? 'knowledge_base_ids' : 'application_ids')

function isIn(projectId: string): boolean {
  const p = projects.projects.find(x => x.id === projectId)
  if (!p) return false
  return ((p as any)[fieldName.value] as string[] || []).includes(props.resourceId)
}

const alreadyIn = computed(() =>
  projects.projects.some(p => isIn(p.id))
)

async function toggle(projectId: string) {
  if (busy.value) return
  busy.value = true
  try {
    if (isIn(projectId)) {
      await projects.detachResource(projectId, props.kind, props.resourceId)
    } else {
      await projects.attachResource(projectId, props.kind, props.resourceId)
    }
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '操作失敗')
  } finally {
    busy.value = false
  }
}
</script>
