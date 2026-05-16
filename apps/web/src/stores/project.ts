/**
 * Project store — workspace-scoped Project（RFC-006 Phase C-1 backend 落地）。
 *
 * 階段 0（已 super-seded）：純前端 + localStorage
 * 階段 1（本檔）：呼叫 backend API（agent service /projects），
 *                activeId 仍存 localStorage 以便 UX 連續。
 */
import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

import {
  projectApi,
  type Project,
  type CreateProjectInput,
  type UpdateProjectInput,
  type ResourceKind,
} from '../api/project'

export type { Project }

const ACTIVE_KEY = 'staffkm.active_project_id'

export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const activeId = ref<string | null>(localStorage.getItem(ACTIVE_KEY))
  const loading  = ref(false)
  const error    = ref<string | null>(null)

  const active = computed<Project | null>(
    () => projects.value.find((p) => p.id === activeId.value) ?? null,
  )

  watch(activeId, (v) => {
    if (v) localStorage.setItem(ACTIVE_KEY, v)
    else   localStorage.removeItem(ACTIVE_KEY)
  })

  async function load() {
    loading.value = true
    error.value = null
    try {
      projects.value = await projectApi.list()
      // 若 activeId 已不在清單裡 → 清空（避免幽靈狀態）
      if (activeId.value && !projects.value.some((p) => p.id === activeId.value)) {
        activeId.value = null
      }
    } catch (e: any) {
      error.value = e?.message || String(e)
    } finally {
      loading.value = false
    }
  }

  async function create(input: CreateProjectInput): Promise<Project> {
    const p = await projectApi.create(input)
    projects.value = [p, ...projects.value]
    activeId.value = p.id
    return p
  }

  async function update(id: string, patch: UpdateProjectInput) {
    const p = await projectApi.update(id, patch)
    const idx = projects.value.findIndex((x) => x.id === id)
    if (idx >= 0) projects.value[idx] = p
    projects.value = [...projects.value]
  }

  async function remove(id: string) {
    await projectApi.remove(id)
    projects.value = projects.value.filter((p) => p.id !== id)
    if (activeId.value === id) activeId.value = projects.value[0]?.id ?? null
  }

  function switchTo(id: string | null) {
    activeId.value = id
  }

  async function attachResource(id: string, kind: ResourceKind, resourceId: string) {
    const p = await projectApi.attachResource(id, kind, resourceId)
    const idx = projects.value.findIndex((x) => x.id === id)
    if (idx >= 0) projects.value[idx] = p
    projects.value = [...projects.value]
  }

  async function detachResource(id: string, kind: ResourceKind, resourceId: string) {
    const p = await projectApi.detachResource(id, kind, resourceId)
    const idx = projects.value.findIndex((x) => x.id === id)
    if (idx >= 0) projects.value[idx] = p
    projects.value = [...projects.value]
  }

  return {
    projects, active, activeId, loading, error,
    load, create, update, remove, switchTo,
    attachResource, detachResource,
  }
})
