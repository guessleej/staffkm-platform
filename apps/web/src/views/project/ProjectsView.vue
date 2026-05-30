<template>
  <div class="flex flex-col h-full">
    <!-- 頁首 -->
    <div class="px-6 py-5 flex-shrink-0">
      <div class="card-hero flex items-center justify-between gap-4">
        <div>
          <h1 class="heading-page heading-accent">Projects</h1>
          <p class="text-sm text-fg-tertiary mt-1">把相關的知識庫 + 應用綁在一起，切換 Project 自動過濾顯示。</p>
        </div>
        <button
          @click="openCreate"
          class="btn btn-primary"
        >
          <SIcon name="plus" :size="16" />
          建立 Project
        </button>
      </div>
    </div>

    <!-- 列表 -->
    <div class="flex-1 overflow-y-auto px-6 pb-6">
      <div v-if="projects.loading" class="flex justify-center py-20">
        <SSpinner :size="28" />
      </div>

      <EmptyState
        v-else-if="!projects.projects.length"
        icon="folder"
        title="尚未建立任何 Project"
        description="建立一個 Project，把相關 KB / App 綁進去，切換時自動過濾"
        action-label="建立第一個 Project"
        @action="openCreate"
      />

      <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <div
          v-for="(p, idx) in projects.projects" :key="p.id"
          class="card-warm fade-up p-5"
          :style="`animation-delay: ${idx * 40}ms`"
          :class="projects.activeId === p.id ? 'ring-1 ring-brand-300' : ''"
        >
          <div class="flex items-start gap-3 mb-3">
            <div class="w-10 h-10 rounded-xl bg-brand-50 flex items-center justify-center text-xl flex-shrink-0">
              {{ p.emoji || '#' }}
            </div>
            <div class="min-w-0 flex-1">
              <h3 class="font-semibold text-sm text-fg truncate">{{ p.name }}</h3>
              <p class="text-[11px] text-fg-tertiary mt-0.5 font-mono">{{ p.id.slice(0, 8) }}</p>
            </div>
            <span
              v-if="projects.activeId === p.id"
              class="px-2 py-0.5 text-[10px] font-semibold rounded-full bg-brand-50 text-brand-700 flex-shrink-0"
            >使用中</span>
          </div>
          <p class="text-xs text-fg-secondary line-clamp-2 min-h-[32px] mb-3">
            {{ p.description || '未填寫說明' }}
          </p>
          <div class="flex items-center gap-3 text-[11px] text-fg-tertiary mb-4">
            <span class="flex items-center gap-1">
              <SIcon name="database" :size="12" />
              {{ p.knowledge_base_ids.length }} KB
            </span>
            <span class="flex items-center gap-1">
              <SIcon name="message-square" :size="12" />
              {{ p.application_ids.length }} App
            </span>
          </div>
          <div class="flex items-center gap-1.5">
            <button
              v-if="projects.activeId !== p.id"
              @click="projects.switchTo(p.id)"
              class="flex-1 text-center text-xs font-medium text-brand-700 bg-brand-50 hover:bg-brand-100 py-1.5 rounded-md transition"
            >切換到此</button>
            <button
              v-else
              @click="projects.switchTo(null)"
              class="flex-1 text-center text-xs font-medium text-fg-secondary bg-neutral-100 hover:bg-neutral-200 py-1.5 rounded-md transition"
            >離開 Project</button>
            <button
              @click="openEdit(p)"
              class="px-2.5 text-fg-tertiary hover:text-brand-600 hover:bg-brand-50 rounded-md py-1.5 transition"
              title="編輯"
            >
              <SIcon name="edit" :size="14" />
            </button>
            <button
              @click="confirmDelete(p)"
              class="px-2.5 text-fg-tertiary hover:text-danger-600 hover:bg-danger-50 rounded-md py-1.5 transition"
              title="刪除"
            >
              <SIcon name="trash" :size="14" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 建立 / 編輯 modal -->
    <Teleport to="body">
      <div
        v-if="showDialog"
        class="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 backdrop-blur-sm p-4"
        @click.self="showDialog = false"
      >
        <div class="w-full max-w-md bg-surface-raised rounded-2xl shadow-2xl overflow-hidden">
          <div class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between">
            <h3 class="font-semibold text-base text-fg">
              {{ editingId ? '編輯 Project' : '建立 Project' }}
            </h3>
            <button @click="showDialog = false" class="p-1 rounded-md text-fg-tertiary hover:text-fg hover:bg-neutral-100">
              <SIcon name="x" :size="16" />
            </button>
          </div>
          <div class="px-5 py-4 space-y-4">
            <div>
              <label class="block text-xs font-semibold text-fg-secondary mb-1.5">圖示</label>
              <input
                v-model="draft.emoji"
                maxlength="2"
                placeholder="#"
                class="w-20 h-10 text-center text-lg rounded-lg border border-neutral-200 focus:border-brand-500 focus:ring-2 focus:ring-brand-100 outline-none"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold text-fg-secondary mb-1.5">
                名稱 <span class="text-danger-500">*</span>
              </label>
              <input
                v-model="draft.name"
                placeholder="例：人事 SOP 諮詢"
                class="form-input"
                @keyup.enter="onSubmit"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold text-fg-secondary mb-1.5">說明</label>
              <textarea
                v-model="draft.description"
                rows="3"
                placeholder="這個 Project 用途為何？"
                class="form-textarea"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold text-fg-secondary mb-1.5">
                System Prompt
                <span class="text-fg-tertiary font-normal">（在此 Project 下對話時的全域指示）</span>
              </label>
              <textarea
                v-model="draft.system_prompt"
                rows="3"
                placeholder="例：請使用繁體中文，所有回覆都帶上文件來源…"
                class="form-textarea font-mono"
              />
            </div>
          </div>
          <div class="px-5 py-3 border-t border-neutral-100 bg-neutral-50/40 flex items-center justify-end gap-2">
            <button
              @click="showDialog = false"
              class="h-9 px-4 text-sm text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50"
            >取消</button>
            <button
              @click="onSubmit"
              :disabled="!draft.name.trim() || submitting"
              class="h-9 px-4 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 disabled:opacity-50 rounded-lg"
            >
              {{ submitting ? '儲存中…' : (editingId ? '儲存' : '建立') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { SIcon, SSpinner } from '@staffkm/ui-kit'
import { useProjectStore, type Project } from '../../stores/project'
import EmptyState from '../../components/common/EmptyState.vue'

const projects = useProjectStore()

const showDialog = ref(false)
const editingId = ref<string | null>(null)
const submitting = ref(false)
const draft = reactive({
  name: '',
  description: '',
  emoji: '#',
  system_prompt: '',
})

function reset() {
  draft.name = ''
  draft.description = ''
  draft.emoji = '#'
  draft.system_prompt = ''
  editingId.value = null
}

function openCreate() {
  reset()
  showDialog.value = true
}

function openEdit(p: Project) {
  editingId.value = p.id
  draft.name = p.name
  draft.description = p.description || ''
  draft.emoji = p.emoji || '#'
  draft.system_prompt = p.system_prompt || ''
  showDialog.value = true
}

async function onSubmit() {
  const name = draft.name.trim()
  if (!name) return
  submitting.value = true
  try {
    const payload = {
      name,
      description: draft.description.trim() || undefined,
      emoji: (draft.emoji || '#').slice(0, 2),
      system_prompt: draft.system_prompt.trim() || undefined,
    }
    if (editingId.value) {
      await projects.update(editingId.value, payload)
    } else {
      await projects.create(payload)
    }
    showDialog.value = false
    reset()
  } finally {
    submitting.value = false
  }
}

async function confirmDelete(p: Project) {
  if (!confirm(`確定要刪除「${p.name}」？KB / App 不會被刪除，只會解除關聯。`)) return
  await projects.remove(p.id)
}

onMounted(() => {
  if (!projects.projects.length) projects.load()
})
</script>
