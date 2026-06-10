import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { DEFAULT_WORKSPACE_ID, workspaceApi, type Workspace } from '../api/workspace'

const STORAGE_KEY = 'staffkm.current_workspace_id'

export const useWorkspaceStore = defineStore('workspace', () => {
  const workspaces = ref<Workspace[]>([])
  const currentId  = ref<string | null>(localStorage.getItem(STORAGE_KEY))
  const loading    = ref(false)

  const current = computed<Workspace | null>(
    () => workspaces.value.find((w) => w.id === currentId.value) ?? null,
  )

  const role = computed(() => current.value?.role ?? null)

  const canWrite = computed(() => {
    const r = role.value
    return r === 'owner' || r === 'admin' || r === 'editor'
  })

  const canManage = computed(() => {
    const r = role.value
    return r === 'owner' || r === 'admin'
  })

  /** 載入使用者所有 workspace；自動選擇 currentId（localStorage 優先，否則第一個）。 */
  async function load() {
    loading.value = true
    try {
      workspaces.value = await workspaceApi.list()
      if (workspaces.value.length === 0) {
        currentId.value = null
        localStorage.removeItem(STORAGE_KEY)
        return
      }
      // localStorage 中的 id 不再有效（被刪除或被 kick）→ 退到第一個
      const stored = currentId.value
      const found = stored && workspaces.value.find((w) => w.id === stored)
      if (!found) {
        const fallback =
          workspaces.value.find((w) => w.id === DEFAULT_WORKSPACE_ID) ??
          workspaces.value[0]
        switchTo(fallback.id)
      }
    } finally {
      loading.value = false
    }
  }

  // race 修：確保 workspace 已解析（currentId 選好）才回。並發呼叫共用同一個 load。
  // 用途：axios 攔截器在送 workspace-scoped 請求前，若 currentId 還沒就緒（剛登入 /
  // 換來源 localStorage 空），先 await 這個 → 避免缺 X-Workspace-ID → gateway 退 legacy → 404。
  let _readyPromise: Promise<void> | null = null
  function ensureReady(): Promise<void> {
    if (currentId.value) return Promise.resolve()
    if (!_readyPromise) {
      _readyPromise = load().finally(() => { _readyPromise = null })
    }
    return _readyPromise
  }

  function switchTo(id: string) {
    currentId.value = id
    localStorage.setItem(STORAGE_KEY, id)
  }

  async function createAndSwitch(input: { name: string; slug: string; description?: string }) {
    const ws = await workspaceApi.create(input)
    workspaces.value = [ws, ...workspaces.value]
    switchTo(ws.id)
    return ws
  }

  async function refresh() {
    await load()
  }

  function reset() {
    workspaces.value = []
    currentId.value = null
    localStorage.removeItem(STORAGE_KEY)
  }

  return {
    workspaces,
    currentId,
    current,
    role,
    canWrite,
    canManage,
    loading,
    load,
    ensureReady,
    switchTo,
    createAndSwitch,
    refresh,
    reset,
  }
})
