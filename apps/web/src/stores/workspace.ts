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
    switchTo,
    createAndSwitch,
    refresh,
    reset,
  }
})
