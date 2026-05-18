<template>
  <div ref="rootRef" class="relative">
    <button
      @click="open = !open"
      :class="[
        'flex items-center gap-1.5 px-2.5 py-1.5 text-sm font-medium rounded-md transition-colors',
        active
          ? 'bg-brand-50 text-brand-700'
          : 'text-fg-secondary hover:bg-neutral-100 hover:text-fg',
      ]"
      :aria-expanded="open"
    >
      <SIcon :name="icon" :size="16" />
      <span>{{ label }}</span>
      <SIcon name="chevron-down" :size="12" :class="open ? 'rotate-180 transition-transform' : 'transition-transform'" />
    </button>

    <div
      v-if="open"
      class="absolute top-full left-1/2 -translate-x-1/2 mt-2 z-50
             bg-surface-raised border border-bd rounded-xl shadow-xl
             min-w-[360px] max-w-[480px] p-3"
      @click.stop
    >
      <div v-for="(group, gi) in groups" :key="gi" class="mb-2 last:mb-0">
        <div v-if="group.label" class="px-2 py-1 text-[10px] uppercase tracking-wider text-fg-tertiary font-semibold">
          {{ group.label }}
        </div>
        <div class="grid grid-cols-2 gap-1">
          <router-link
            v-for="item in group.items"
            :key="item.to"
            :to="item.to"
            @click="open = false"
            class="flex items-start gap-2 p-2 rounded-md hover:bg-neutral-50 transition-colors text-left group"
          >
            <SIcon :name="item.icon" :size="14" class="text-fg-tertiary mt-0.5 flex-shrink-0 group-hover:text-brand-600" />
            <div class="flex-1 min-w-0">
              <div class="text-xs font-medium text-fg truncate">{{ item.label }}</div>
              <div v-if="item.desc" class="text-[11px] text-fg-tertiary truncate">{{ item.desc }}</div>
            </div>
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { SIcon } from '@staffkm/ui-kit'

interface MenuItem { to: string; label: string; icon: string; desc?: string }
interface MenuGroup { label?: string; items: MenuItem[] }

const props = defineProps<{
  label: string
  icon: string
  groups: MenuGroup[]
}>()

const open = ref(false)
const rootRef = ref<HTMLElement | null>(null)
const route = useRoute()

const active = computed(() =>
  props.groups.some(g => g.items.some(i => route.path.startsWith(i.to)))
)

function onClickOutside(e: MouseEvent) {
  if (rootRef.value && !rootRef.value.contains(e.target as Node)) open.value = false
}
onMounted(() => document.addEventListener('click', onClickOutside))
onBeforeUnmount(() => document.removeEventListener('click', onClickOutside))
</script>
