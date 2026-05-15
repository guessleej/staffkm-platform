<template>
  <div class="flex flex-col h-full">
    <div class="h-14 border-b border-gray-200 px-6 flex items-center justify-between bg-white">
      <h2 class="font-semibold text-gray-800">知識庫管理</h2>
      <button @click="showCreate = true"
        class="flex items-center gap-2 bg-indigo-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-indigo-700 transition">
        ＋ 建立知識庫
      </button>
    </div>

    <div class="flex-1 overflow-auto p-6">
      <div v-if="loading" class="text-center py-12 text-gray-400">載入中…</div>
      <div v-else-if="!kbs.length" class="text-center py-12">
        <p class="text-4xl mb-3">📚</p>
        <p class="text-gray-500">尚未建立任何知識庫</p>
      </div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <div
          v-for="kb in kbs"
          :key="kb.id"
          class="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition"
        >
          <div class="flex items-start justify-between mb-3">
            <div class="flex items-center gap-2">
              <span class="text-2xl">📖</span>
              <h3 class="font-semibold text-gray-800">{{ kb.name }}</h3>
            </div>
            <span class="text-xs px-2 py-0.5 rounded-full" :class="statusClass(kb.status)">
              {{ statusLabel(kb.status) }}
            </span>
          </div>
          <p class="text-sm text-gray-500 mb-4 line-clamp-2">{{ kb.description || '（無說明）' }}</p>
          <div class="flex gap-2">
            <router-link :to="`/knowledge/${kb.id}/documents`"
              class="flex-1 text-center text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 py-1.5 rounded-lg transition">
              文件管理
            </router-link>
            <router-link :to="`/knowledge/${kb.id}/hit-test`"
              class="flex-1 text-center text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 py-1.5 rounded-lg transition">
              命中測試
            </router-link>
            <button @click="deleteKB(kb.id)"
              class="text-sm bg-red-50 hover:bg-red-100 text-red-600 px-3 py-1.5 rounded-lg transition">
              刪除
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 建立 Modal -->
  <Teleport to="body">
    <div v-if="showCreate" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50" @click.self="showCreate = false">
      <div class="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-md">
        <h3 class="font-bold text-gray-900 mb-4">建立知識庫</h3>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">名稱 <span class="text-red-500">*</span></label>
            <input v-model="form.name" type="text" placeholder="例：人事法規知識庫"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">說明</label>
            <textarea v-model="form.description" rows="3" placeholder="說明此知識庫的用途"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none resize-none" />
          </div>
        </div>
        <div class="flex gap-3 mt-5">
          <button @click="showCreate = false" class="flex-1 text-sm border border-gray-300 text-gray-700 py-2 rounded-lg hover:bg-gray-50">取消</button>
          <button @click="createKB" :disabled="!form.name" class="flex-1 text-sm bg-indigo-600 text-white py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition">建立</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { knowledgeApi } from '../../api/knowledge'

const kbs = ref<any[]>([])
const loading = ref(true)
const showCreate = ref(false)
const form = ref({ name: '', description: '' })

function statusClass(s: string) {
  return {
    active: 'bg-green-100 text-green-700',
    building: 'bg-yellow-100 text-yellow-700',
    error: 'bg-red-100 text-red-700',
    disabled: 'bg-gray-100 text-gray-500',
  }[s] ?? 'bg-gray-100 text-gray-500'
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
  if (!confirm('確定要刪除此知識庫？其下的文件與向量資料也將一併刪除。')) return
  await knowledgeApi.deleteBase(id)
  await load()
}

onMounted(load)
</script>
