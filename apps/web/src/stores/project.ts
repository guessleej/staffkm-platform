/**
 * Project store — workspace 下的「資源組合」抽象（RFC-006 B-5 scaffold）。
 *
 * Project 把 application_ids / knowledge_base_ids / 自訂指令 打包成一個
 * 工作空間，讓使用者可在不同情境（部門 SOP / 客戶 RFP / 內部研發）間切換。
 *
 * 階段 0（本 PR）：純前端 + localStorage，無 backend 表。
 * 階段 1（後續 PR）：落 DB（project / project_member / project_resource）
 *                  + REST API + workspace scoped。
 */
import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

export interface Project {
  id:                   string
  name:                 string
  description?:         string
  emoji?:               string                // 暫存：未來改成 svg icon ref
  knowledge_base_ids:   string[]
  application_ids:      string[]
  system_prompt?:       string
  created_at:           string
  updated_at:           string
}

const STORAGE_KEY = 'staffkm.projects.v0'
const ACTIVE_KEY  = 'staffkm.active_project_id'

function loadFromLocal(): Project[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function saveToLocal(items: Project[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
}

export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>(loadFromLocal())
  const activeId = ref<string | null>(localStorage.getItem(ACTIVE_KEY))

  const active = computed<Project | null>(
    () => projects.value.find((p) => p.id === activeId.value) ?? null,
  )

  // 任何 mutation 後自動 persist
  watch(projects, (v) => saveToLocal(v), { deep: true })
  watch(activeId, (v) => {
    if (v) localStorage.setItem(ACTIVE_KEY, v)
    else   localStorage.removeItem(ACTIVE_KEY)
  })

  function create(input: { name: string; description?: string; emoji?: string }): Project {
    const now = new Date().toISOString()
    const p: Project = {
      id: crypto.randomUUID(),
      name: input.name,
      description: input.description,
      emoji: input.emoji,
      knowledge_base_ids: [],
      application_ids: [],
      created_at: now,
      updated_at: now,
    }
    projects.value = [p, ...projects.value]
    activeId.value = p.id
    return p
  }

  function update(id: string, patch: Partial<Project>) {
    const idx = projects.value.findIndex((p) => p.id === id)
    if (idx < 0) return
    projects.value[idx] = {
      ...projects.value[idx],
      ...patch,
      updated_at: new Date().toISOString(),
    }
    // 觸發 reactivity
    projects.value = [...projects.value]
  }

  function remove(id: string) {
    projects.value = projects.value.filter((p) => p.id !== id)
    if (activeId.value === id) activeId.value = projects.value[0]?.id ?? null
  }

  function switchTo(id: string | null) {
    activeId.value = id
  }

  function attachResource(id: string, kind: 'kb' | 'app', resourceId: string) {
    const p = projects.value.find((x) => x.id === id)
    if (!p) return
    const list = kind === 'kb' ? p.knowledge_base_ids : p.application_ids
    if (list.includes(resourceId)) return
    list.push(resourceId)
    update(id, kind === 'kb'
      ? { knowledge_base_ids: list }
      : { application_ids: list })
  }

  function detachResource(id: string, kind: 'kb' | 'app', resourceId: string) {
    const p = projects.value.find((x) => x.id === id)
    if (!p) return
    if (kind === 'kb') update(id, { knowledge_base_ids: p.knowledge_base_ids.filter((x) => x !== resourceId) })
    else               update(id, { application_ids:    p.application_ids.filter((x) => x !== resourceId) })
  }

  return {
    projects, active, activeId,
    create, update, remove, switchTo,
    attachResource, detachResource,
  }
})
