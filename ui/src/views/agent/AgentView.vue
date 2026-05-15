<template>
  <div class="flex flex-col h-full">
    <div class="h-14 border-b border-gray-200 px-6 flex items-center bg-white">
      <h2 class="font-semibold text-gray-800">AI 代理人</h2>
    </div>
    <div class="flex-1 overflow-auto p-6">
      <p class="text-sm text-gray-500 mb-6">
        以下是系統內建的行政場景 AI 代理人，點選「立即諮詢」可直接開始對話。
      </p>
      <div v-if="loading" class="text-center py-12 text-gray-400">載入中…</div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <div v-for="agent in agents" :key="agent.scenario_id"
          class="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition">
          <div class="flex items-center gap-3 mb-3">
            <div class="w-10 h-10 bg-indigo-100 rounded-xl flex items-center justify-center text-xl">
              {{ scenarioIcon(agent.scenario_id) }}
            </div>
            <h3 class="font-semibold text-gray-800">{{ agent.name }}</h3>
          </div>
          <p class="text-sm text-gray-500 mb-4">{{ agent.description }}</p>
          <div class="mb-4">
            <p class="text-xs font-medium text-gray-400 mb-2">建議問題：</p>
            <ul class="space-y-1">
              <li v-for="q in agent.suggested_questions.slice(0, 3)" :key="q"
                class="text-xs text-indigo-700 bg-indigo-50 rounded-lg px-3 py-1.5 line-clamp-1">
                {{ q }}
              </li>
            </ul>
          </div>
          <router-link to="/chat"
            @click="startChat(agent.scenario_id)"
            class="block text-center text-sm bg-indigo-600 hover:bg-indigo-700 text-white py-2 rounded-lg transition">
            立即諮詢
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '../../api/index'
import { chatApi } from '../../api/chat'

const agents = ref<any[]>([])
const loading = ref(true)
const router = useRouter()

const ICONS: Record<string, string> = {
  official_doc: '📋',
  hr_leave: '👤',
  procurement: '🛒',
  budget: '💰',
  sop: '📑',
  onboarding: '🎓',
}
function scenarioIcon(id: string) { return ICONS[id] ?? '🤖' }

async function load() {
  const { data } = await http.get('/agents')
  agents.value = data.data || []
  loading.value = false
}

async function startChat(scenarioId: string) {
  const conv = await chatApi.createConversation(scenarioId)
  router.push({ path: '/chat', query: { conv: conv.conversation_id } })
}

onMounted(load)
</script>
