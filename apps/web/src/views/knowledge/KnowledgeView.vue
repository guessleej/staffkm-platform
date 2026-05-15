<template>
  <div class="flex flex-col h-full">
    <!-- 頁首 -->
    <div class="px-6 py-5 border-b border-neutral-200 bg-surface-raised flex items-center justify-between flex-shrink-0">
      <div>
        <h1 class="text-lg font-semibold text-neutral-900">知識庫</h1>
        <p class="text-xs text-neutral-500 mt-0.5">共 {{ kbs.length }} 個</p>
      </div>
      <button
        @click="showCreate = true"
        class="inline-flex items-center gap-1.5 h-9 px-4 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-lg transition-colors shadow-sm"
      >
        <IconPlus :size="14" :stroke-width="2.5" />
        建立知識庫
      </button>
    </div>

    <!-- 列表 -->
    <div class="flex-1 overflow-auto p-6">
      <div v-if="loading" class="flex items-center justify-center py-20 text-neutral-400 gap-2 text-sm">
        <IconSpinner :size="16" /> 載入中
      </div>

      <!-- 空狀態 -->
      <div v-else-if="!kbs.length" class="flex flex-col items-center justify-center py-20">
        <div class="w-16 h-16 rounded-full bg-neutral-100 flex items-center justify-center text-neutral-400 mb-4">
          <IconKnowledge :size="28" :stroke-width="1.5" />
        </div>
        <p class="text-sm font-medium text-neutral-700 mb-1">尚未建立知識庫</p>
        <p class="text-xs text-neutral-500 mb-5 max-w-xs text-center">
          建立一個知識庫，再上傳文件、設定檢索方式
        </p>
        <button
          @click="showCreate = true"
          class="inline-flex items-center gap-1.5 h-9 px-4 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-lg transition-colors"
        >
          <IconPlus :size="14" :stroke-width="2.5" />
          建立第一個
        </button>
      </div>

      <!-- 卡片列表 -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <div
          v-for="kb in kbs"
          :key="kb.id"
          class="bg-surface-raised rounded-xl border border-neutral-200 hover:border-brand-300 hover:shadow-md transition-all overflow-hidden"
        >
          <div class="px-5 pt-5 pb-4">
            <div class="flex items-start justify-between mb-3 gap-3">
              <div class="flex items-start gap-3 min-w-0">
                <div class="w-9 h-9 rounded-lg flex items-center justify-center text-brand-600 bg-brand-50 flex-shrink-0">
                  <IconKnowledge :size="18" />
                </div>
                <div class="min-w-0">
                  <h3 class="font-semibold text-sm text-neutral-900 truncate">{{ kb.name }}</h3>
                  <p class="text-[11px] text-neutral-400 mt-0.5 font-mono">{{ kb.id.slice(0, 8) }}</p>
                </div>
              </div>
              <span class="text-[11px] px-2 py-0.5 rounded-full font-medium flex-shrink-0" :class="statusClass(kb.status)">
                {{ statusLabel(kb.status) }}
              </span>
            </div>
            <p class="text-xs text-neutral-500 line-clamp-2 min-h-[32px]">
              {{ kb.description || '尚未填寫說明' }}
            </p>
          </div>
          <div class="px-3 pb-3 pt-0 flex gap-1.5">
            <router-link
              :to="`/knowledge/${kb.id}/documents`"
              class="flex-1 text-center text-xs font-medium text-neutral-700 bg-neutral-100 hover:bg-neutral-200 py-1.5 rounded-md transition-colors"
            >
              文件
            </router-link>
            <router-link
              :to="`/knowledge/${kb.id}/hit-test`"
              class="flex-1 text-center text-xs font-medium text-neutral-700 bg-neutral-100 hover:bg-neutral-200 py-1.5 rounded-md transition-colors"
            >
              檢索測試
            </router-link>
            <button
              @click="deleteKB(kb.id)"
              class="px-2 text-neutral-400 hover:text-danger-600 hover:bg-danger-50 rounded-md transition-colors"
              title="刪除"
            >
              <IconDelete :size="14" />
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 建立 Modal -->
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0"
      leave-active-class="transition duration-150 ease-in"
      leave-to-class="opacity-0"
    >
      <div
        v-if="showCreate"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-900/40 backdrop-blur-sm"
        @click.self="showCreate = false"
      >
        <div class="w-full max-w-md bg-surface-raised rounded-2xl shadow-2xl overflow-hidden">
          <div class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between">
            <h3 class="font-semibold text-base text-neutral-900">建立知識庫</h3>
            <button @click="showCreate = false" class="p-1 rounded-md text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100">
              <IconClose :size="14" />
            </button>
          </div>
          <div class="px-5 py-4 space-y-4">
            <div>
              <label class="block text-xs font-semibold text-neutral-600 mb-1.5">
                名稱 <span class="text-danger-500">*</span>
              </label>
              <input
                v-model="form.name"
                type="text"
                placeholder="例：人事法規、採購規範"
                class="w-full text-sm border border-neutral-200 rounded-lg px-3 py-2 focus:outline-none focus:border-brand-500 focus:shadow-focus"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold text-neutral-600 mb-1.5">說明</label>
              <textarea
                v-model="form.description"
                rows="3"
                placeholder="這個知識庫的用途、適用對象等"
                class="w-full text-sm border border-neutral-200 rounded-lg px-3 py-2 focus:outline-none focus:border-brand-500 focus:shadow-focus resize-none"
              />
            </div>
          </div>
          <div class="px-5 py-3 border-t border-neutral-100 bg-neutral-50 flex items-center justify-end gap-2">
            <button
              @click="showCreate = false"
              class="h-9 px-4 text-sm text-neutral-700 bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50"
            >
              取消
            </button>
            <button
              @click="createKB"
              :disabled="!form.name"
              class="h-9 px-4 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg"
            >
              建立
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { knowledgeApi } from '../../api/knowledge'
import { IconClose, IconDelete, IconKnowledge, IconPlus, IconSpinner } from '../../components/icons'

const kbs = ref<any[]>([])
const loading = ref(true)
const showCreate = ref(false)
const form = ref({ name: '', description: '' })

function statusClass(s: string) {
  return {
    active:   'bg-success-50 text-success-700',
    building: 'bg-warning-50 text-warning-700',
    error:    'bg-danger-50 text-danger-600',
    disabled: 'bg-neutral-100 text-neutral-500',
  }[s] ?? 'bg-neutral-100 text-neutral-500'
}
function statusLabel(s: string) {
  return { active: '正常', building: '建構中', error: '錯誤', disabled: '停用' }[s] ?? s
}

async function load() {
  loading.value = true
  const data = await knowledgeApi.listBases()
  kbs.value = data.data || []
  loading.value = false
}

async function createKB() {
  await knowledgeApi.createBase(form.value)
  showCreate.value = false
  form.value = { name: '', description: '' }
  await load()
}

async function deleteKB(id: string) {
  if (!confirm('確定要刪除？其下的文件與向量資料會一併移除。')) return
  await knowledgeApi.deleteBase(id)
  await load()
}

onMounted(load)
</script>
