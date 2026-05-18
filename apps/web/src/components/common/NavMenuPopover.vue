<template>
  <div ref="rootRef" class="relative inline-block">
    <button
      @click.stop="open = !open"
      :class="[
        'flex items-center gap-1.5 px-2.5 py-1.5 text-sm font-medium rounded-md transition-colors whitespace-nowrap',
        active
          ? 'bg-brand-50 text-brand-700'
          : 'text-fg-secondary hover:bg-neutral-100 hover:text-fg',
      ]"
      :aria-expanded="open"
    >
      <SIcon :name="icon" :size="16" />
      <span>{{ label }}</span>
      <SIcon name="chevron-down" :size="12" />
    </button>

    <!-- Teleport 到 body 跳出 parent overflow-x-auto / z-index 限制 -->
    <Teleport to="body">
      <div
        v-if="open"
        :style="dropdownStyle"
        class="fixed z-[9999] bg-surface-raised border border-bd rounded-xl shadow-2xl py-2 w-[260px] max-h-[80vh] overflow-y-auto"
        @click.stop
      >
        <div v-for="(group, gi) in groups" :key="gi">
          <div v-if="group.label" class="px-3 pt-2 pb-1 text-[10px] uppercase tracking-wider text-fg-tertiary font-semibold">
            {{ group.label }}
          </div>
          <router-link
            v-for="item in group.items"
            :key="item.to"
            :to="item.to"
            @click="open = false"
            class="flex items-center gap-2 px-3 py-1.5 hover:bg-neutral-50 transition-colors text-sm"
          >
            <SIcon :name="item.icon" :size="14" class="text-fg-tertiary flex-shrink-0" />
            <span class="text-fg truncate">{{ item.label }}</span>
          </router-link>
          <div v-if="gi < groups.length - 1" class="my-1 border-t border-neutral-100"></div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { SIcon } from '@staffkm/ui-kit'

interface MenuItem { to: string; label: string; icon: string }
interface MenuGroup { label?: string; items: MenuItem[] }

const props = defineProps<{
  label: string
  icon: string
  groups: MenuGroup[]
}>()

const open = ref(false)
const rootRef = ref<HTMLElement | null>(null)
const route = useRoute()
const dropdownStyle = ref<Record<string, string>>({})

const active = computed(() =>
  props.groups.some(g => g.items.some(i => route.path.startsWith(i.to)))
)

async function position() {
  if (!rootRef.value) return
  await nextTick()
  const r = rootRef.value.getBoundingClientRect()
  const dropdownW = 260
  let left = r.left + r.width / 2 - dropdownW / 2
  // clamp 不超出視窗
  left = Math.max(8, Math.min(left, window.innerWidth - dropdownW - 8))
  dropdownStyle.value = {
    top: `${r.bottom + 6}px`,
    left: `${left}px`,
  }
}

watch(open, async (v) => {
  if (v) await position()
})

function onClickOutside(e: MouseEvent) {
  if (!rootRef.value) return
  if (rootRef.value.contains(e.target as Node)) return
  open.value = false
}
function onResize() { if (open.value) position() }

onMounted(() => {
  document.addEventListener('click', onClickOutside)
  window.addEventListener('resize', onResize)
  window.addEventListener('scroll', onResize, true)
})
onBeforeUnmount(() => {
  document.removeEventListener('click', onClickOutside)
  window.removeEventListener('resize', onResize)
  window.removeEventListener('scroll', onResize, true)
})
</script>
