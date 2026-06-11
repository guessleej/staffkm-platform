<template>
  <div class="flex flex-col h-full">
    <div class="px-6 py-5 flex-shrink-0">
      <div class="card-hero flex items-center justify-between gap-4">
        <div>
          <h1 class="heading-page heading-accent">Skills（可重用 prompt 技能）</h1>
          <p class="text-xs text-fg-tertiary mt-1">共 {{ items.length }} 個</p>
        </div>
        <button
          @click="showCreate = true"
          class="btn btn-primary"
        >
          <IconPlus :size="14" :stroke-width="2.5" />
          建立 Skill
        </button>
      </div>
    </div>

    <div class="flex-1 overflow-auto px-6 pb-6">
      <!-- 教學：如何自己做一個 Skill（可收合）-->
      <div class="mb-4 bg-surface-raised border border-bd rounded-xl overflow-hidden">
        <button
          @click="showHelp = !showHelp"
          class="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-neutral-50 transition"
        >
          <span class="text-sm font-semibold text-fg flex items-center gap-2"><SIcon name="book-open" :size="16" class="text-brand-600" /> 如何自己做一個 Skill？</span>
          <span class="text-xs text-fg-tertiary">{{ showHelp ? '收合 ▲' : '展開 ▼' }}</span>
        </button>
        <div v-if="showHelp" class="px-5 pb-5 text-sm text-fg-secondary space-y-3 border-t border-bd">
          <p class="pt-3">
            Skill 是<strong class="text-fg">可重用的 prompt 範本</strong>：寫一次，就能在多個 Application
            或對話流程裡重複呼叫，不用每次重打提示詞。
          </p>
          <div>
            <p class="font-medium text-fg mb-1">三步驟</p>
            <ol class="list-decimal list-inside space-y-1">
              <li>點右上角 <strong class="text-fg">建立 Skill</strong>。</li>
              <li>填三欄：<strong class="text-fg">名稱</strong>（識別用）、<strong class="text-fg">說明</strong>（這個 skill 做什麼）、<strong class="text-fg">Prompt template</strong>（實際的提示詞）。</li>
              <li>在 Prompt template 用 <code v-pre class="px-1 py-0.5 bg-neutral-100 rounded text-brand-700 font-mono text-xs">{{變數}}</code> 當佔位 → 呼叫時帶入不同值，同一個 Skill 就能套用到不同情境。</li>
            </ol>
          </div>
          <div>
            <p class="font-medium text-fg mb-1">範例</p>
            <pre v-pre class="px-3 py-2 bg-neutral-50 rounded-lg font-mono text-[12px] text-neutral-700 whitespace-pre-wrap border border-neutral-200">名稱：公文摘要
說明：把冗長公文濃縮成重點
Prompt template：
請把以下公文摘要成 3 點重點，並標出主旨與辦理期限：

{{內容}}</pre>
            <p class="text-xs text-fg-tertiary mt-1.5">
              呼叫時把實際公文內容塞進 <code v-pre class="px-1 bg-neutral-100 rounded text-brand-700 font-mono">{{內容}}</code>，就會自動套出摘要。
            </p>
          </div>
          <p class="text-xs text-fg-tertiary flex items-start gap-1.5">
            <SIcon name="lightbulb" :size="13" class="mt-0.5 shrink-0 text-amber-500" />
            <span>小提示：變數用<strong class="text-fg">雙大括號</strong> <code v-pre class="px-1 bg-neutral-100 rounded font-mono">{{ }}</code>、命名取清楚；建好的 Skill 之後可在 <strong class="text-fg">Application 流程節點</strong>裡選用。</span>
          </p>
        </div>
      </div>

      <p v-if="loading" class="text-sm text-fg-tertiary">載入中…</p>
      <EmptyState
        v-else-if="!items.length"
        icon="sparkles"
        title="尚未建立 Skill"
        description="Skill 是可重用的 prompt 範本，可在多個 Application 中呼叫"
        action-label="建立第一個 Skill"
        @action="showCreate = true"
      />
      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div
          v-for="(s, idx) in items" :key="s.id"
          class="card-warm fade-up p-5"
          :style="`animation-delay: ${idx * 40}ms`"
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
              <input v-model="draft.name" class="form-input" @keydown.enter="(e) => { if (!(e as any).isComposing) { onCreate() } }" />
            </div>
            <div>
              <label class="block text-xs text-neutral-500 mb-1">說明</label>
              <input v-model="draft.description" class="form-input" />
            </div>
            <div>
              <label class="block text-xs text-neutral-500 mb-1">Prompt template</label>
              <textarea v-model="draft.prompt_template" rows="4" class="w-full px-3 py-2 text-sm font-mono rounded-md border border-neutral-200 resize-none focus:outline-none focus:ring-1 focus:ring-brand-400" placeholder="例：請扮演 {{role}}，回答關於 {{topic}} 的問題。" />
              <p class="text-[11px] text-fg-tertiary mt-1 flex items-start gap-1">
                <SIcon name="lightbulb" :size="12" class="mt-0.5 shrink-0 text-amber-500" />
                <span v-pre>用 {{變數}} 當佔位，呼叫時帶入不同值（例：{{內容}}、{{role}}）。</span>
              </p>
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
import { SIcon } from '@staffkm/ui-kit'
import { IconPlus } from '../../components/icons'
import EmptyState from '../../components/common/EmptyState.vue'
import { useDialog } from '../../composables/useDialog'
import { useToast } from '../../composables/useToast'

const dialog = useDialog()
const toast = useToast()

const items = ref<SkillEntity[]>([])
const loading = ref(true)
const showCreate = ref(false)
const showHelp = ref(true)   // 教學卡：預設展開、可收合
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
  if (!(await dialog.confirm('確定要刪除此 Skill？此動作無法復原。', { tone: 'danger', confirmLabel: '刪除' }))) return
  try {
    await skillApi.remove(id)
    toast.success('Skill 已刪除')
    await load()
  } catch (e: any) {
    toast.error('刪除失敗：' + (e?.message || e))
  }
}
onMounted(load)
</script>
