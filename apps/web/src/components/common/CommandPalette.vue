<template>
  <Teleport to="body">
    <transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0"
      leave-active-class="transition duration-100 ease-in"
      leave-to-class="opacity-0"
    >
      <div
        v-if="open"
        class="fixed inset-0 z-[400] flex items-start justify-center pt-[15vh] px-4 bg-black/40"
        @click.self="close"
        @keydown.esc="close"
      >
        <div
          ref="panelRef"
          class="w-full max-w-xl bg-surface-raised rounded-2xl shadow-2xl overflow-hidden border border-neutral-200"
          role="dialog"
          aria-modal="true"
          aria-labelledby="cmdk-input"
        >
          <input
            id="cmdk-input"
            ref="inputRef"
            v-model="query"
            class="w-full px-5 py-3 text-base bg-transparent border-b border-neutral-100 focus:outline-none placeholder:text-neutral-400"
            placeholder="搜尋指令或頁面…"
            @keydown.down.prevent="move(1)"
            @keydown.up.prevent="move(-1)"
            @keydown.enter.prevent="exec()"
          />
          <ul
            ref="listRef"
            class="max-h-[60vh] overflow-y-auto py-2"
            role="listbox"
            aria-label="指令清單"
          >
            <li v-if="!filtered.length" class="px-5 py-6 text-sm text-neutral-400 text-center">
              查無項目
            </li>
            <li
              v-for="(c, i) in filtered"
              :key="c.id"
              :class="['mx-2 px-3 py-2 rounded-lg cursor-pointer flex items-center gap-3',
                       i === active ? 'bg-brand-50 text-brand-700' : 'hover:bg-neutral-50']"
              role="option"
              :aria-selected="i === active"
              @mousemove="active = i"
              @click="exec(i)"
            >
              <span class="text-base flex-shrink-0 w-5 text-center">{{ c.icon || '•' }}</span>
              <span class="flex-1 text-sm">{{ c.label }}</span>
              <span v-if="c.shortcut" class="text-[10px] text-neutral-400 font-mono">{{ c.shortcut }}</span>
            </li>
          </ul>
          <div class="px-5 py-2 border-t border-neutral-100 bg-neutral-50 text-[10px] text-neutral-400 flex items-center gap-3">
            <span><kbd class="cmdk-kbd">↑</kbd><kbd class="cmdk-kbd">↓</kbd> 移動</span>
            <span><kbd class="cmdk-kbd">Enter</kbd> 執行</span>
            <span><kbd class="cmdk-kbd">Esc</kbd> 關閉</span>
            <span class="ml-auto"><kbd class="cmdk-kbd">⌘</kbd><kbd class="cmdk-kbd">K</kbd> 開啟</span>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'

interface CmdItem {
  id:       string
  label:    string
  icon?:    string
  shortcut?:string
  to?:      string
  action?:  () => void | Promise<void>
  roles?:   string[]
}

const router = useRouter()
const auth   = useAuthStore()

const open    = ref(false)
const query   = ref('')
const active  = ref(0)
const panelRef = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)
const listRef  = ref<HTMLElement | null>(null)

const allCommands = computed<CmdItem[]>(() => [
  { id: 'go-chat',       label: '前往對話',         icon: '💬', to: '/chat' },
  { id: 'go-apps',       label: '前往應用',         icon: '▢', to: '/applications' },
  { id: 'go-knowledge',  label: '前往知識庫',       icon: '◫', to: '/knowledge' },
  { id: 'go-agents',     label: '前往代理人',       icon: '◉', to: '/agents' },
  { id: 'go-tools',      label: '前往工具',         icon: '⚙', to: '/tools' },
  { id: 'go-skills',     label: '前往 Skills',      icon: '✦', to: '/skills' },
  { id: 'go-datasource', label: '前往資料來源',     icon: '⌬', to: '/data-sources' },
  { id: 'go-users',      label: '管理 / 使用者',    icon: '◴', to: '/admin/users',   roles: ['admin'] },
  { id: 'go-models',     label: '管理 / 模型供應商', icon: '◦', to: '/admin/models',  roles: ['admin'] },
  { id: 'go-usage',      label: '管理 / Token 用量', icon: '◓', to: '/admin/usage',  roles: ['admin'] },
  { id: 'go-system',     label: '管理 / 系統設定',  icon: '◑', to: '/admin/system',  roles: ['admin'] },
  { id: 'logout',        label: '登出',             icon: '↗', action: async () => { await auth.logout?.(); router.push('/login') } },
])

const filtered = computed<CmdItem[]>(() => {
  const q = query.value.trim().toLowerCase()
  let list = allCommands.value.filter(c =>
    !c.roles || auth.hasRole?.(c.roles)
  )
  if (q) list = list.filter(c => c.label.toLowerCase().includes(q))
  return list
})

watch(open, async (v) => {
  if (v) {
    query.value = ''
    active.value = 0
    await nextTick()
    inputRef.value?.focus()
  }
})

watch(filtered, () => { active.value = 0 })

function move(d: number) {
  const n = filtered.value.length
  if (!n) return
  active.value = (active.value + d + n) % n
  scrollToActive()
}
function scrollToActive() {
  nextTick(() => {
    const el = listRef.value?.querySelectorAll('li')[active.value] as HTMLElement | undefined
    el?.scrollIntoView({ block: 'nearest' })
  })
}
async function exec(i?: number) {
  const idx = i ?? active.value
  const c = filtered.value[idx]
  if (!c) return
  close()
  if (c.to) router.push(c.to)
  else if (c.action) await c.action()
}
function close() { open.value = false }

function onKeydown(e: KeyboardEvent) {
  // Cmd/Ctrl + K toggle
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    open.value = !open.value
  }
}

onMounted(() => { window.addEventListener('keydown', onKeydown) })
onBeforeUnmount(() => { window.removeEventListener('keydown', onKeydown) })
</script>

<style scoped>
.cmdk-kbd {
  display: inline-block;
  padding: 0 4px;
  border: 1px solid hsl(var(--color-neutral-200));
  border-radius: 4px;
  background: hsl(var(--color-surface-raised));
  font-family: ui-monospace, "SF Mono", monospace;
  font-size: 10px;
}
</style>
