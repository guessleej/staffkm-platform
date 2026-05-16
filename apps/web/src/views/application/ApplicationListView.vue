<template>
  <div class="flex-1 flex flex-col overflow-hidden">
    <!-- 頁首 -->
    <div class="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between flex-shrink-0">
      <div>
        <h1 class="text-lg font-semibold text-gray-900">{{ $t('app.title') }}</h1>
        <p class="text-sm text-gray-500 mt-0.5">建立並管理各部門的 AI 問答應用</p>
      </div>
      <button v-if="auth.hasRole(['admin'])" @click="openCreateDialog" class="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
        </svg>
        {{ $t('app.createApp') }}
      </button>
    </div>

    <!-- 應用卡片列表 -->
    <div class="flex-1 overflow-y-auto p-6">
      <div v-if="loading" class="flex justify-center py-20">
        <svg class="animate-spin w-8 h-8 text-indigo-500" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
        </svg>
      </div>

      <div v-else-if="applications.length === 0" class="text-center py-20">
        <div class="w-16 h-16 bg-indigo-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <svg class="w-8 h-8 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/>
          </svg>
        </div>
        <p class="text-gray-600 font-medium">尚無任何應用</p>
        <p class="text-gray-400 text-sm mt-1">點擊右上角新增您的第一個 AI 應用</p>
      </div>

      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        <div
          v-for="app in applications"
          :key="app.id"
          class="relative bg-white rounded-xl border p-5 hover:shadow-md transition-all cursor-pointer group"
          :class="batch.isSelected(app.id)
            ? 'border-indigo-400 ring-1 ring-indigo-200'
            : 'border-gray-200 hover:border-indigo-300'"
          @click="batch.hasSelection ? batch.toggle(app.id) : enterApp(app)"
        >
          <!-- 批量選取 checkbox（hover 或選中時顯示）-->
          <button
            class="absolute top-3 right-3 w-5 h-5 flex items-center justify-center rounded border transition opacity-0 group-hover:opacity-100"
            :class="batch.isSelected(app.id)
              ? 'bg-indigo-600 border-indigo-600 text-white opacity-100'
              : 'bg-white border-gray-300 hover:border-indigo-400 text-transparent'"
            @click.stop="batch.toggle(app.id)"
            :title="batch.isSelected(app.id) ? '取消選取' : '選取此項'"
          >
            <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
            </svg>
          </button>

          <!-- 應用圖示 -->
          <div class="w-11 h-11 rounded-xl flex items-center justify-center text-2xl mb-4"
               :style="{ background: appGradient(app.id) }">
            {{ app.icon || appEmoji(app.name) }}
          </div>

          <!-- 名稱與描述 -->
          <h3 class="font-semibold text-gray-900 text-sm group-hover:text-indigo-600 transition-colors">{{ app.name }}</h3>
          <p class="text-xs text-gray-400 mt-1 line-clamp-2 min-h-[2rem]">{{ app.description || '暫無描述' }}</p>

          <!-- 標籤 -->
          <div class="flex items-center gap-2 mt-4">
            <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold"
                  :class="app.type === 'workflow' ? 'bg-purple-100 text-purple-700' : 'bg-indigo-100 text-indigo-700'">
              {{ app.type === 'workflow' ? '工作流' : '簡易問答' }}
            </span>
            <span v-if="app.knowledge_base_ids?.length" class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-700">
              {{ app.knowledge_base_ids.length }} 個知識庫
            </span>
          </div>

          <!-- 管理員操作 -->
          <div v-if="auth.hasRole(['admin'])" class="flex gap-2 mt-4 pt-4 border-t border-gray-100 opacity-0 group-hover:opacity-100 transition-opacity" @click.stop>
            <button v-if="app.type === 'workflow'" @click.stop="router.push(`/applications/${app.id}/workflow`)"
                    class="flex-1 text-center text-xs text-purple-500 hover:text-purple-700 py-1 rounded-lg hover:bg-purple-50 transition font-medium">
              編輯流程
            </button>
            <button @click.stop="openEditDialog(app)" class="flex-1 text-center text-xs text-gray-500 hover:text-indigo-600 py-1 rounded-lg hover:bg-indigo-50 transition">
              編輯
            </button>
            <button @click.stop="openShareDialog(app)" class="flex-1 text-center text-xs text-gray-500 hover:text-teal-600 py-1 rounded-lg hover:bg-teal-50 transition" title="分享連結">
              分享
            </button>
            <button @click.stop="openApiKeyDialog(app)" class="flex-1 text-center text-xs text-gray-500 hover:text-amber-600 py-1 rounded-lg hover:bg-amber-50 transition" title="API Keys">
              API Key
            </button>
            <button @click.stop="deleteApp(app.id)" class="flex-1 text-center text-xs text-gray-500 hover:text-rose-600 py-1 rounded-lg hover:bg-rose-50 transition">
              刪除
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 分享連結 Dialog -->
    <div v-if="showShareDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
        <div class="px-6 pt-6 pb-4 border-b border-gray-100 flex items-center justify-between">
          <h3 class="text-base font-semibold text-gray-900">分享連結</h3>
          <button @click="showShareDialog = false" class="text-gray-400 hover:text-gray-600 transition">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>
        <div class="p-6 space-y-4">
          <!-- 未公開警示 -->
          <div v-if="!shareTargetApp?.is_public" class="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
            <p class="font-semibold mb-1">此應用尚未公開</p>
            <p>請先在「編輯」中啟用<span class="font-semibold">「公開應用（所有使用者可看到）」</span>選項，才能讓外部人員透過連結存取。</p>
          </div>
          <!-- 公開連結 -->
          <div v-else>
            <p class="text-sm text-gray-600 mb-3">任何人皆可透過此連結使用此應用程式，無需登入。</p>
            <div class="flex items-center gap-2">
              <input
                :value="shareUrl"
                readonly
                class="flex-1 px-3 py-2 text-sm rounded-lg border border-gray-200 bg-gray-50 text-gray-700 select-all focus:outline-none"
                @click="($event.target as HTMLInputElement).select()"
              />
              <button
                @click="copyShareUrl"
                class="flex-shrink-0 px-3 py-2 bg-indigo-600 text-white text-xs font-medium rounded-lg hover:bg-indigo-700 transition"
              >
                {{ shareCopied ? '已複製！' : '複製' }}
              </button>
            </div>
            <a
              :href="shareUrl"
              target="_blank"
              class="mt-3 flex items-center gap-1.5 text-xs text-indigo-500 hover:text-indigo-700 transition"
            >
              <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
              </svg>
              在新分頁開啟
            </a>
          </div>
        </div>
        <div class="px-6 pb-6 pt-2 flex justify-end">
          <button @click="showShareDialog = false" class="px-4 py-2 border border-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition">關閉</button>
        </div>
      </div>
    </div>

    <!-- API Key 管理 Dialog -->
    <div v-if="showApiKeyDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
        <!-- 標題 -->
        <div class="px-6 pt-6 pb-4 border-b border-gray-100 flex-shrink-0 flex items-center justify-between">
          <h3 class="text-base font-semibold text-gray-900">{{ apiKeyTargetApp?.name }} — API Keys</h3>
          <button @click="closeApiKeyDialog" class="text-gray-400 hover:text-gray-600 transition">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto p-6 space-y-5">
          <!-- 新建立的 Key 顯示區（一次性警示） -->
          <div v-if="newlyCreatedKey" class="bg-amber-50 border border-amber-300 rounded-xl p-4">
            <div class="flex items-start gap-2 mb-2">
              <svg class="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
              </svg>
              <div>
                <p class="text-sm font-semibold text-amber-800">請立即複製此 API Key — 之後將無法再次查看完整金鑰</p>
              </div>
            </div>
            <div class="flex items-center gap-2 mt-2">
              <code class="flex-1 bg-white border border-amber-200 rounded-lg px-3 py-2 text-sm font-mono text-gray-800 break-all select-all">{{ newlyCreatedKey }}</code>
              <button @click="copyKey(newlyCreatedKey)" class="flex-shrink-0 px-3 py-2 bg-amber-600 text-white text-xs font-medium rounded-lg hover:bg-amber-700 transition">
                {{ copied ? '已複製！' : '複製' }}
              </button>
            </div>
          </div>

          <!-- 現有 Keys 列表 -->
          <div>
            <h4 class="text-sm font-semibold text-gray-700 mb-3">現有 API Keys</h4>
            <div v-if="apiKeysLoading" class="flex justify-center py-6">
              <svg class="animate-spin w-6 h-6 text-indigo-500" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
            </div>
            <div v-else-if="apiKeys.length === 0" class="text-center py-6 text-gray-400 text-sm">
              尚無 API Keys，請點擊下方「建立新 Key」
            </div>
            <div v-else class="overflow-x-auto rounded-xl border border-gray-200">
              <table class="min-w-full divide-y divide-gray-100">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="px-4 py-2 text-left text-xs font-semibold text-gray-500">名稱</th>
                    <th class="px-4 py-2 text-left text-xs font-semibold text-gray-500">前綴</th>
                    <th class="px-4 py-2 text-left text-xs font-semibold text-gray-500">狀態</th>
                    <th class="px-4 py-2 text-left text-xs font-semibold text-gray-500">建立時間</th>
                    <th class="px-4 py-2 text-left text-xs font-semibold text-gray-500">到期時間</th>
                    <th class="px-4 py-2 text-right text-xs font-semibold text-gray-500">操作</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-100 bg-white">
                  <tr v-for="key in apiKeys" :key="key.id">
                    <td class="px-4 py-2.5 text-sm text-gray-800">{{ key.name }}</td>
                    <td class="px-4 py-2.5">
                      <code class="text-xs font-mono bg-gray-100 px-2 py-0.5 rounded text-gray-600">{{ key.key_prefix }}…</code>
                    </td>
                    <td class="px-4 py-2.5">
                      <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold"
                            :class="key.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'">
                        {{ key.is_active ? '啟用' : '停用' }}
                      </span>
                    </td>
                    <td class="px-4 py-2.5 text-xs text-gray-500">{{ formatDate(key.created_at) }}</td>
                    <td class="px-4 py-2.5 text-xs text-gray-500">{{ key.expires_at ? formatDate(key.expires_at) : '永不到期' }}</td>
                    <td class="px-4 py-2.5 text-right">
                      <div class="flex justify-end gap-1">
                        <button @click="toggleKey(key)" class="text-xs px-2 py-1 rounded-lg transition"
                                :class="key.is_active ? 'text-gray-500 hover:text-amber-600 hover:bg-amber-50' : 'text-gray-500 hover:text-emerald-600 hover:bg-emerald-50'">
                          {{ key.is_active ? '停用' : '啟用' }}
                        </button>
                        <button @click="removeKey(key.id)" class="text-xs px-2 py-1 rounded-lg text-gray-500 hover:text-rose-600 hover:bg-rose-50 transition">
                          刪除
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- 建立新 Key 表單 -->
          <div class="border border-gray-200 rounded-xl p-4 space-y-3">
            <h4 class="text-sm font-semibold text-gray-700">+ 建立新 Key</h4>
            <div class="grid grid-cols-2 gap-3">
              <div class="col-span-2 sm:col-span-1">
                <label class="form-label">Key 名稱 <span class="text-rose-500">*</span></label>
                <input v-model="newKeyForm.name" class="form-input" placeholder="如：生產環境整合"/>
              </div>
              <div class="col-span-2 sm:col-span-1">
                <label class="form-label">有效天數（選填，留空永不過期）</label>
                <input v-model.number="newKeyForm.expires_days" type="number" min="1" class="form-input" placeholder="如：365"/>
              </div>
            </div>
            <div class="flex justify-end">
              <button @click="createKey" :disabled="!newKeyForm.name || creatingKey"
                      class="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition disabled:opacity-50">
                {{ creatingKey ? '建立中…' : '建立 Key' }}
              </button>
            </div>
          </div>
        </div>

        <div class="px-6 pb-6 pt-4 border-t border-gray-100 flex justify-end flex-shrink-0">
          <button @click="closeApiKeyDialog" class="px-4 py-2 border border-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition">關閉</button>
        </div>
      </div>
    </div>

    <!-- 建立/編輯應用 Dialog -->
    <div v-if="showDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-xl overflow-hidden flex flex-col max-h-[90vh]">
        <div class="px-6 pt-6 pb-4 border-b border-gray-100 flex-shrink-0">
          <h3 class="text-base font-semibold text-gray-900">{{ editingApp ? '編輯應用' : '新增 AI 應用' }}</h3>
        </div>

        <div class="flex-1 overflow-y-auto p-6 space-y-5">
          <div class="grid grid-cols-2 gap-4">
            <div class="col-span-2">
              <label class="form-label">應用名稱 <span class="text-rose-500">*</span></label>
              <input v-model="form.name" class="form-input" placeholder="如：人事請假助理"/>
            </div>
            <div class="col-span-2">
              <label class="form-label">描述</label>
              <input v-model="form.description" class="form-input" placeholder="簡短說明此應用的用途"/>
            </div>
          </div>

          <div>
            <label class="form-label">歡迎訊息</label>
            <textarea v-model="form.welcome_message" rows="2" class="form-input resize-none"
                      placeholder="您好！我是…，可以幫您查詢…"></textarea>
          </div>

          <div>
            <label class="form-label">系統提示詞（System Prompt）</label>
            <textarea v-model="form.system_prompt" rows="5" class="form-input resize-none font-mono text-xs"
                      placeholder="你是一位…請根據知識庫內容…"></textarea>
          </div>

          <div>
            <label class="form-label">建議問題（每行一題）</label>
            <textarea v-model="suggestedQuestionsText" rows="3" class="form-input resize-none text-sm"
                      placeholder="如何申請出差？&#10;請假流程是什麼？"></textarea>
          </div>

          <div>
            <label class="form-label">關聯知識庫</label>
            <div v-if="knowledgeBases.length === 0" class="text-xs text-gray-400">
              尚無知識庫，請先在「知識庫管理」頁面建立
            </div>
            <div v-else class="flex flex-wrap gap-2 mt-1">
              <label
                v-for="kb in knowledgeBases"
                :key="kb.id"
                class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border cursor-pointer text-sm transition-all"
                :class="form.knowledge_base_ids.includes(kb.id)
                  ? 'border-indigo-400 bg-indigo-50 text-indigo-700'
                  : 'border-gray-200 hover:border-gray-300 text-gray-700'"
              >
                <input type="checkbox" :value="kb.id" v-model="form.knowledge_base_ids" class="hidden"/>
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/>
                </svg>
                {{ kb.name }}
              </label>
            </div>
          </div>

          <!-- Reranker 設定 -->
          <div>
            <label class="form-label">Reranker 模型（選填）</label>
            <div v-if="rerankerModels.length === 0" class="text-xs text-gray-400 py-1">
              尚無 Reranker 模型，請至<span class="text-indigo-500 mx-1">模型供應商</span>設定
            </div>
            <select v-else v-model="form.config.reranker_model_id" class="form-input">
              <option value="">不使用 Reranker</option>
              <option v-for="m in rerankerModels" :key="m.id" :value="m.id">
                {{ m.display_name || m.model_name }}
              </option>
            </select>
          </div>

          <div class="flex items-center gap-2">
            <input id="is_public" v-model="form.is_public" type="checkbox" class="w-4 h-4 accent-indigo-600"/>
            <label for="is_public" class="text-sm text-gray-700">公開應用（所有使用者可看到）</label>
          </div>
        </div>

        <div class="px-6 pb-6 pt-4 border-t border-gray-100 flex justify-end gap-3 flex-shrink-0">
          <button @click="showDialog = false" class="px-4 py-2 border border-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition">取消</button>
          <button @click="saveApp" class="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition disabled:opacity-50" :disabled="saving || !form.name">
            {{ saving ? '儲存中…' : (editingApp ? '儲存變更' : '建立應用') }}
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- 批量選擇浮動工具列 -->
  <BatchSelectToolbar :count="batch.count" @clear="batch.clear()">
    <button
      v-if="auth.hasRole(['admin'])"
      @click="batchDelete"
      class="px-2.5 py-1.5 rounded-lg text-sm text-white/90 hover:bg-white/10 hover:text-white transition"
    >刪除</button>
  </BatchSelectToolbar>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { applicationApi, type Application } from '../../api/application'
import { apiKeyApi, type ApiKey } from '../../api/apiKey'
import { modelProviderApi, type AiModel } from '../../api/modelProvider'
import { http } from '../../api/index'
import { useBatchSelect } from '../../composables/useBatchSelect'
import BatchSelectToolbar from '../../components/common/BatchSelectToolbar.vue'

const router = useRouter()
const auth = useAuthStore()

const loading = ref(false)
const saving = ref(false)
const applications = ref<Application[]>([])

// ── 批量選擇 ───────────────────────────────────────────────────────────
const batch = useBatchSelect()

async function batchDelete() {
  const ids = Array.from(batch.selected.value)
  if (ids.length === 0) return
  if (!confirm(`確定要刪除 ${ids.length} 個應用？此操作無法復原。`)) return
  for (const id of ids) {
    try { await applicationApi.delete(id) } catch { /* swallow */ }
  }
  applications.value = applications.value.filter(a => !ids.includes(a.id))
  batch.clear()
}
const knowledgeBases = ref<any[]>([])
const rerankerModels = ref<AiModel[]>([])
const showDialog = ref(false)
const editingApp = ref<Application | null>(null)

// ── 分享連結狀態 ─────────────────────────────────────────────────────────────
const showShareDialog = ref(false)
const shareTargetApp = ref<Application | null>(null)
const shareCopied = ref(false)

const shareUrl = computed(() =>
  shareTargetApp.value ? `${window.location.origin}/share/${shareTargetApp.value.id}` : ''
)

function openShareDialog(app: Application) {
  shareTargetApp.value = app
  shareCopied.value = false
  showShareDialog.value = true
}

async function copyShareUrl() {
  if (!shareUrl.value) return
  try {
    await navigator.clipboard.writeText(shareUrl.value)
    shareCopied.value = true
    setTimeout(() => { shareCopied.value = false }, 2000)
  } catch {
    // fallback
  }
}

// ── API Key 管理狀態 ─────────────────────────────────────────────────────────
const showApiKeyDialog = ref(false)
const apiKeyTargetApp = ref<Application | null>(null)
const apiKeys = ref<ApiKey[]>([])
const apiKeysLoading = ref(false)
const newlyCreatedKey = ref<string | null>(null)
const copied = ref(false)
const creatingKey = ref(false)
const newKeyForm = reactive({ name: '', expires_days: undefined as number | undefined })

const form = reactive({
  name: '',
  description: '',
  welcome_message: '',
  system_prompt: '',
  knowledge_base_ids: [] as string[],
  is_public: true,
  suggested_questions: [] as string[],
  config: { reranker_model_id: '' } as Record<string, any>,
})
const suggestedQuestionsText = computed({
  get: () => form.suggested_questions.join('\n'),
  set: (v) => { form.suggested_questions = v.split('\n').map(s => s.trim()).filter(Boolean) },
})

async function load() {
  loading.value = true
  try {
    const [appsRes, kbRes, rerankerRes] = await Promise.all([
      applicationApi.list({ page_size: 50 }),
      http.get('/knowledge/bases', { params: { page_size: 50 } }),
      modelProviderApi.listModels(undefined, 'reranker'),
    ])
    applications.value = appsRes.data.data?.items ?? appsRes.data.data ?? []
    knowledgeBases.value = kbRes.data.data?.items ?? kbRes.data.data ?? []
    const rerankerData = rerankerRes.data.data
    rerankerModels.value = Array.isArray(rerankerData)
      ? rerankerData
      : (rerankerData?.items ?? [])
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  editingApp.value = null
  Object.assign(form, { name: '', description: '', welcome_message: '', system_prompt: '', knowledge_base_ids: [], is_public: true, suggested_questions: [], config: { reranker_model_id: '' } })
  showDialog.value = true
}

function openEditDialog(app: Application) {
  editingApp.value = app
  const appConfig = typeof app.config === 'string' ? JSON.parse(app.config || '{}') : (app.config ?? {})
  Object.assign(form, {
    name: app.name,
    description: app.description ?? '',
    welcome_message: app.welcome_message ?? '',
    system_prompt: app.system_prompt ?? '',
    knowledge_base_ids: [...(app.knowledge_base_ids ?? [])],
    is_public: app.is_public,
    suggested_questions: [...(app.suggested_questions ?? [])],
    config: { reranker_model_id: appConfig.reranker_model_id ?? '' },
  })
  showDialog.value = true
}

async function saveApp() {
  saving.value = true
  try {
    // 清理 config：若未選擇 reranker 則移除空欄位
    const configPayload: Record<string, any> = { ...form.config }
    if (!configPayload.reranker_model_id) {
      delete configPayload.reranker_model_id
    }
    const payload = { ...form, config: configPayload }
    if (editingApp.value) {
      await applicationApi.update(editingApp.value.id, payload)
    } else {
      await applicationApi.create(payload)
    }
    showDialog.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function deleteApp(id: string) {
  if (!confirm('確定要刪除此應用？')) return
  await applicationApi.delete(id)
  applications.value = applications.value.filter(a => a.id !== id)
}

function enterApp(app: Application) {
  router.push(`/applications/${app.id}/chat`)
}

function appGradient(id: string) {
  const hue = parseInt(id.slice(-4), 16) % 360
  return `linear-gradient(135deg, hsl(${hue},70%,88%), hsl(${(hue + 40) % 360},70%,88%))`
}

// ── API Key 操作 ─────────────────────────────────────────────────────────────

async function openApiKeyDialog(app: Application) {
  apiKeyTargetApp.value = app
  newlyCreatedKey.value = null
  copied.value = false
  Object.assign(newKeyForm, { name: '', expires_days: undefined })
  showApiKeyDialog.value = true
  await loadApiKeys(app.id)
}

function closeApiKeyDialog() {
  showApiKeyDialog.value = false
  apiKeyTargetApp.value = null
  newlyCreatedKey.value = null
  apiKeys.value = []
}

async function loadApiKeys(appId: string) {
  apiKeysLoading.value = true
  try {
    const res = await apiKeyApi.list(appId)
    apiKeys.value = res.data?.data?.data ?? res.data?.data ?? []
  } finally {
    apiKeysLoading.value = false
  }
}

async function createKey() {
  if (!newKeyForm.name || !apiKeyTargetApp.value) return
  creatingKey.value = true
  try {
    const payload: { name: string; application_id: string; expires_days?: number } = {
      name: newKeyForm.name,
      application_id: apiKeyTargetApp.value.id,
    }
    if (newKeyForm.expires_days) payload.expires_days = newKeyForm.expires_days
    const res = await apiKeyApi.create(payload)
    const created = res.data?.data?.data ?? res.data?.data
    newlyCreatedKey.value = created?.full_key ?? null
    Object.assign(newKeyForm, { name: '', expires_days: undefined })
    await loadApiKeys(apiKeyTargetApp.value.id)
  } finally {
    creatingKey.value = false
  }
}

async function toggleKey(key: ApiKey) {
  await apiKeyApi.toggle(key.id)
  if (apiKeyTargetApp.value) await loadApiKeys(apiKeyTargetApp.value.id)
}

async function removeKey(id: string) {
  if (!confirm('確定要刪除此 API Key？此操作無法復原。')) return
  await apiKeyApi.remove(id)
  if (apiKeyTargetApp.value) await loadApiKeys(apiKeyTargetApp.value.id)
}

async function copyKey(key: string) {
  try {
    await navigator.clipboard.writeText(key)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {
    // fallback
  }
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('zh-TW', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

function appEmoji(name: string) {
  const map: Record<string, string> = { 'sop': 'SOP', '請假': '假', '採購': '購', '財務': '財', '人事': '人', '公文': '文', '法規': '法', '知識': '知' }
  for (const [k, v] of Object.entries(map)) {
    if (name.includes(k)) return v
  }
  return 'APP'
}

onMounted(load)
</script>

<style scoped>
.form-label { @apply block text-xs font-semibold text-gray-600 mb-1; }
.form-input { @apply w-full px-3 py-2 text-sm rounded-lg border border-gray-200 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 outline-none transition; }
</style>
