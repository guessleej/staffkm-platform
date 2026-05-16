<template>
  <div class="flex flex-col h-full">
    <div class="px-6 py-5 border-b border-neutral-200 bg-surface-raised flex items-center justify-between flex-shrink-0">
      <div>
        <h1 class="text-lg font-semibold text-neutral-900">Skills（可重用 prompt 技能）</h1>
        <p class="text-xs text-neutral-500 mt-0.5">共 {{ items.length }} 個</p>
      </div>
      <button
        @click="showCreate = true"
        class="inline-flex items-center gap-1.5 h-9 px-4 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-lg transition-colors shadow-sm"
      >
        <IconPlus :size="14" :stroke-width="2.5" />
        建立 Skill
      </button>
    </div>

    <div class="flex-1 overflow-auto p-6">
      <p v-if="loading" class="text-sm text-neutral-400">載入中…</p>
      <div v-else-if="!items.length" class="text-center py-20 text-sm text-neutral-500">
        尚未建立 Skill。Skill 是可重用的 prompt 範本，可在多個 Application 中呼叫。
      </div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div
          v-for="s in items" :key="s.id"
          class="bg-surface-raised rounded-xl border border-neutral-200 hover:border-brand-300 hover:shadow-md transition-all p-5"
        >
          <div class="flex items-center justify-between mb-2">
            <h3 class="font-semibold text-sm text-neutral-900 truncate">{{ s.name }}</h3>
            <button @click="onDelete(s.id)" class="text-xs text-neutral-400 hover:text-danger-600 transition">刪除</button>
          </div>
          <p class="text-xs text-neutral-500 line-clamp-2 min-h-[2rem]">
            {{ s.description || '尚未填寫說明' }}
          </p>
          <pre class="mt-3 px-3 py-2 text-[11px] bg-neutral-50 rounded font-mono text-neutral-700 line-clamp-3 whitespace-pre-wrap">{{ s.prompt_template || '（未設定 prompt template）' }}</pre>
          <div v-if="s.tags?.length" class="mt-2 flex flex-wrap gap-1">
            <span v-for="t in s.tags" :key="t" class="text-[10px] px-1.5 py-0.5 bg-brand-50 text-brand-700 rounded">{{ t }}</span>
          </div>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div
        v-if="showCreate"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30"
        @click.self="showCreate = false"
      >
        <div class="w-full max-w-md bg-surface-raised rounded-2xl shadow-2xl overflow-hidden">
          <div class="px-5 py-4 border-b border-neutral-100"><h3 class="text-sm font-semibold">建立 Skill</h3></div>
          <div class="px-5 py-4 space-y-3">
            <div>
              <label class="block text-xs text-neutral-500 mb-1">名稱</label>
              <input v-model="draft.name" class="w-full h-9 px-3 text-sm rounded-md border border-neutral-200 focus:outline-none focus:ring-1 focus:ring-brand-400" />
            </div>
            <div>
              <label class="block text-xs text-neutral-500 mb-1">說明</label>
              <input v-model="draft.description" class="w-full h-9 px-3 text-sm rounded-md border border-neutral-200 focus:outline-none focus:ring-1 focus:ring-brand-400" />
            </div>
            <div>
              <label class="block text-xs text-neutral-500 mb-1">Prompt template</label>
              <textarea v-model="draft.prompt_template" rows="4" class="w-full px-3 py-2 text-sm font-mono rounded-md border border-neutral-200 resize-none focus:outline-none focus:ring-1 focus:ring-brand-400" placeholder="例：請扮演 {{role}}，回答關於 {{topic}} 的問題。" />
            </div>
          </div>
          <div class="px-5 py-3 border-t border-neutral-100 bg-neutral-50 flex justify-end gap-2">
            <button @click="showCreate = false" class="h-9 px-4 text-sm rounded-lg border border-neutral-200">取消</button>
            <button :disabled="!draft.name.trim()" @click="onCreate" class="h-9 px-4 text-sm rounded-lg bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-40">建立</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { skillApi, type SkillEntity } from '../../api/extras'
import { IconPlus } from '../../components/icons'

const items = ref<SkillEntity[]>([])
const loading = ref(true)
const showCreate = ref(false)
const draft = reactive({ name: '', description: '', prompt_template: '' })

async function load() {
  loading.value = true
  try { items.value = await skillApi.list() } finally { loading.value = false }
}
async function onCreate() {
  if (!draft.name.trim()) return
  await skillApi.create({
    name: draft.name,
    description: draft.description || undefined,
    prompt_template: draft.prompt_template,
  })
  draft.name = ''; draft.description = ''; draft.prompt_template = ''
  showCreate.value = false
  await load()
}
async function onDelete(id: string) {
  if (!confirm('確定要刪除此 Skill？')) return
  await skillApi.remove(id); await load()
}
onMounted(load)
</script>
