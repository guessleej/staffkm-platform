<template>
  <div ref="rootRef" class="relative">
    <button
      @click="open = !open"
      class="h-8 flex items-center gap-2 px-2.5 rounded-lg text-sm border border-neutral-200 hover:bg-neutral-50 transition"
    >
      <span class="text-base leading-none">{{ store.active?.emoji || '#' }}</span>
      <span class="text-neutral-700 truncate max-w-[160px]">
        {{ store.active?.name || $t('common.noData') }}
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
      <div
        v-if="open"
        class="absolute left-0 mt-1.5 w-72 z-50
               bg-surface-raised rounded-xl border border-neutral-200 shadow-lg
               overflow-hidden"
      >
        <!-- 列表 -->
        <ul v-if="store.projects.length" class="max-h-72 overflow-y-auto py-1">
          <li v-for="p in store.projects" :key="p.id">
            <button
              @click="pick(p.id)"
              class="w-full flex items-start gap-2 px-3 py-2 text-left text-sm hover:bg-neutral-50 transition"
              :class="store.activeId === p.id ? 'bg-neutral-50' : ''"
            >
              <span class="text-base leading-none mt-0.5">{{ p.emoji || '#' }}</span>
              <div class="flex-1 min-w-0">
                <p class="font-medium text-neutral-900 truncate">{{ p.name }}</p>
                <p v-if="p.description" class="text-xs text-neutral-500 truncate">
                  {{ p.description }}
                </p>
                <p class="text-[10px] text-neutral-400 mt-0.5">
                  {{ p.knowledge_base_ids.length }} KB · {{ p.application_ids.length }} App
                </p>
              </div>
            </button>
          </li>
        </ul>
        <p v-else class="px-3 py-4 text-center text-xs text-neutral-400">
          尚未建立任何 Project
        </p>

        <!-- footer -->
        <div class="border-t border-neutral-100 p-1">
          <button
            @click="newDialog = true; open = false"
            class="w-full flex items-center gap-2 px-3 py-2 text-sm text-neutral-700 hover:bg-neutral-100 rounded-lg transition"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
            </svg>
            建立 Project
          </button>
          <button
            v-if="store.active"
            @click="store.switchTo(null); open = false"
            class="w-full flex items-center gap-2 px-3 py-2 text-sm text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900 rounded-lg transition"
          >
            離開目前 Project
          </button>
        </div>
      </div>
    </transition>

    <!-- 建立 Project 簡易表單（modal）-->
    <teleport to="body">
      <div
        v-if="newDialog"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
        @click.self="newDialog = false"
      >
        <div class="w-full max-w-sm bg-surface-raised rounded-2xl shadow-xl overflow-hidden">
          <div class="px-5 py-4 border-b border-neutral-100">
            <h3 class="text-sm font-semibold text-neutral-900">建立 Project</h3>
          </div>
          <div class="px-5 py-4 space-y-3">
            <div>
              <label class="block text-xs text-neutral-500 mb-1">圖示</label>
              <input
                v-model="draft.emoji"
                maxlength="2"
                placeholder="例：#"
                class="w-16 h-9 px-2 text-center text-base rounded-md border border-neutral-200 focus:outline-none focus:ring-1 focus:ring-brand-400"
              />
            </div>
            <div>
              <label class="block text-xs text-neutral-500 mb-1">名稱</label>
              <input
                v-model="draft.name"
                placeholder="例：人事 SOP 諮詢"
                class="w-full h-9 px-3 text-sm rounded-md border border-neutral-200 focus:outline-none focus:ring-1 focus:ring-brand-400"
              />
            </div>
            <div>
              <label class="block text-xs text-neutral-500 mb-1">描述（選填）</label>
              <textarea
                v-model="draft.description"
                rows="2"
                placeholder="這個 Project 用途為何？"
                class="w-full px-3 py-2 text-sm rounded-md border border-neutral-200 focus:outline-none focus:ring-1 focus:ring-brand-400 resize-none"
              />
            </div>
          </div>
          <div class="px-5 py-3 border-t border-neutral-100 flex justify-end gap-2">
            <button
              @click="newDialog = false"
              class="px-3 py-1.5 text-sm rounded-lg text-neutral-600 hover:bg-neutral-100 transition"
            >{{ $t('common.cancel') }}</button>
            <button
              :disabled="!draft.name.trim()"
              @click="confirmCreate"
              class="px-3 py-1.5 text-sm rounded-lg bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed transition"
            >{{ $t('common.create') }}</button>
          </div>
        </div>
      </div>
    </teleport>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { onClickOutside } from '@vueuse/core'
import { useProjectStore } from '../../stores/project'

const store = useProjectStore()

const open = ref(false)
const rootRef = ref<HTMLElement | null>(null)
onClickOutside(rootRef, () => { open.value = false })

const newDialog = ref(false)
const draft = reactive({ name: '', description: '', emoji: '#' })

function pick(id: string) {
  store.switchTo(id)
  open.value = false
}

function confirmCreate() {
  const name = draft.name.trim()
  if (!name) return
  store.create({
    name,
    description: draft.description.trim() || undefined,
    emoji: (draft.emoji || '#').slice(0, 2),
  })
  draft.name = ''
  draft.description = ''
  draft.emoji = '#'
  newDialog.value = false
}
</script>
