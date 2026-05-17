<template>
  <div class="flex h-full">
    <!-- D-5 後續：Application folder 側欄 -->
    <EntityFolderSidebar
      kind="app"
      root-label="所有應用"
      :active-folder-id="activeFolderId"
      @update:active-folder-id="(v) => (activeFolderId = v)"
    />
    <div class="flex-1 flex flex-col overflow-hidden">
    <!-- 頁首 -->
    <div class="bg-surface-raised border-b border-neutral-200 px-6 py-4 flex items-center justify-between flex-shrink-0">
      <div>
        <h1 class="text-lg font-semibold text-fg">{{ $t('app.title') }}</h1>
        <p class="text-sm text-fg-tertiary mt-0.5">建立並管理各部門的 AI 問答應用</p>
      </div>
      <button v-if="auth.hasRole(['admin'])" @click="openCreateDialog" class="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition">
        <SIcon name="plus" :size="16" />
        {{ $t('app.createApp') }}
      </button>
    </div>

    <!-- 應用卡片列表 -->
    <div class="flex-1 overflow-y-auto p-6">
      <div v-if="loading" class="flex justify-center py-20">
        <SSpinner :size="32" />
      </div>

      <div v-else-if="applications.length === 0" class="text-center py-20">
        <div class="w-16 h-16 bg-indigo-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <SIcon name="message-square" :size="32" :stroke-width="1.5" class="text-indigo-400" />
        </div>
        <p class="text-fg-secondary font-medium">尚無任何應用</p>
        <p class="text-fg-tertiary text-sm mt-1">點擊右上角新增您的第一個 AI 應用</p>
      </div>

      <template v-else>
        <!-- D-6：Project 過濾指示 chip -->
        <div
          v-if="activeProject"
          class="mb-4 inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-brand-50 text-brand-700 text-xs"
        >
          <span class="text-base leading-none">{{ activeProject.emoji || '#' }}</span>
          <span>目前 Project：{{ activeProject.name }}（顯示 {{ displayedApps.length }} / {{ applications.length }} 個）</span>
          <button
            @click="projects.switchTo(null)"
            class="text-brand-500 hover:text-brand-700 transition text-base leading-none"
            title="清除 Project 過濾"
          >×</button>
        </div>

        <div v-if="activeProject && !displayedApps.length" class="text-center py-20 text-sm text-neutral-500">
          此 Project 尚未掛任何應用
        </div>
        <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          <div
            v-for="app in displayedApps"
          :key="app.id"
          class="relative bg-surface-raised rounded-2xl border p-5 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200 cursor-pointer group"
          :class="batch.isSelected(app.id)
            ? 'border-brand-400 ring-1 ring-brand-200'
            : 'border-neutral-200 hover:border-brand-200'"
          @click="batch.hasSelection ? batch.toggle(app.id) : enterApp(app)"
        >
          <!-- 批量選取 checkbox（hover 或選中時顯示）-->
          <button
            class="absolute top-3 right-3 w-5 h-5 flex items-center justify-center rounded border transition opacity-0 group-hover:opacity-100"
            :class="batch.isSelected(app.id)
              ? 'bg-indigo-600 border-indigo-600 text-white opacity-100'
              : 'bg-surface-raised border-neutral-300 hover:border-indigo-400 text-transparent'"
            @click.stop="batch.toggle(app.id)"
            :title="batch.isSelected(app.id) ? '取消選取' : '選取此項'"
          >
            <SIcon name="check" :size="12" :stroke-width="3" />
          </button>

          <!-- 應用圖示 -->
          <div class="w-11 h-11 rounded-xl flex items-center justify-center text-2xl mb-4"
               :style="{ background: appGradient(app.id) }">
            {{ app.icon || appEmoji(app.name) }}
          </div>

          <!-- 名稱與描述 -->
          <h3 class="font-semibold text-fg text-sm group-hover:text-indigo-600 transition-colors">{{ app.name }}</h3>
          <p class="text-xs text-fg-tertiary mt-1 line-clamp-2 min-h-[2rem]">{{ app.description || '暫無描述' }}</p>

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
          <div v-if="auth.hasRole(['admin'])" class="flex gap-2 mt-4 pt-4 border-t border-neutral-100 opacity-0 group-hover:opacity-100 transition-opacity" @click.stop>
            <button v-if="app.type === 'workflow'" @click.stop="router.push(`/applications/${app.id}/workflow`)"
                    class="flex-1 text-center text-xs text-purple-500 hover:text-purple-700 py-1 rounded-lg hover:bg-purple-50 transition font-medium">
              編輯流程
            </button>
            <button @click.stop="openEditDialog(app)" class="flex-1 text-center text-xs text-fg-tertiary hover:text-indigo-600 py-1 rounded-lg hover:bg-indigo-50 transition">
              編輯
            </button>
            <button @click.stop="openShareDialog(app)" class="flex-1 text-center text-xs text-fg-tertiary hover:text-teal-600 py-1 rounded-lg hover:bg-teal-50 transition" title="分享連結">
              分享
            </button>
            <button @click.stop="openApiKeyDialog(app)" class="flex-1 text-center text-xs text-fg-tertiary hover:text-amber-600 py-1 rounded-lg hover:bg-amber-50 transition" title="API Keys">
              API Key
            </button>
            <button @click.stop="deleteApp(app.id)" class="flex-1 text-center text-xs text-fg-tertiary hover:text-rose-600 py-1 rounded-lg hover:bg-rose-50 transition">
              刪除
            </button>
          </div>
        </div>
      </div>
      </template>
    </div>

    <!-- 分享連結 Dialog -->
    <div v-if="showShareDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div class="bg-surface-raised rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
        <div class="px-6 pt-6 pb-4 border-b border-neutral-100 flex items-center justify-between">
          <h3 class="text-base font-semibold text-fg">分享連結</h3>
          <button @click="showShareDialog = false" class="text-fg-tertiary hover:text-fg-secondary transition">
            <SIcon name="x" :size="20" />
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
            <p class="text-sm text-fg-secondary mb-3">任何人皆可透過此連結使用此應用程式，無需登入。</p>
            <div class="flex items-center gap-2">
              <input
                :value="shareUrl"
                readonly
                class="flex-1 px-3 py-2 text-sm rounded-lg border border-neutral-200 bg-surface-sunken text-fg-secondary select-all focus:outline-none"
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
              <SIcon name="external-link" :size="14" />
              在新分頁開啟
            </a>
          </div>
        </div>
        <div class="px-6 pb-6 pt-2 flex justify-end">
          <button @click="showShareDialog = false" class="px-4 py-2 border border-neutral-200 text-fg-secondary text-sm font-medium rounded-lg hover:bg-surface-sunken transition">關閉</button>
        </div>
      </div>
    </div>

    <!-- API Key 管理 Dialog -->
    <div v-if="showApiKeyDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div class="bg-surface-raised rounded-2xl shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
        <!-- 標題 -->
        <div class="px-6 pt-6 pb-4 border-b border-neutral-100 flex-shrink-0 flex items-center justify-between">
          <h3 class="text-base font-semibold text-fg">{{ apiKeyTargetApp?.name }} — API Keys</h3>
          <button @click="closeApiKeyDialog" class="text-fg-tertiary hover:text-fg-secondary transition">
            <SIcon name="x" :size="20" />
          </button>
        </div>

        <div class="flex-1 overflow-y-auto p-6 space-y-5">
          <!-- 新建立的 Key 顯示區（一次性警示） -->
          <div v-if="newlyCreatedKey" class="bg-amber-50 border border-amber-300 rounded-xl p-4">
            <div class="flex items-start gap-2 mb-2">
              <SIcon name="alert-triangle" :size="20" class="text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <p class="text-sm font-semibold text-amber-800">請立即複製此 API Key — 之後將無法再次查看完整金鑰</p>
              </div>
            </div>
            <div class="flex items-center gap-2 mt-2">
              <code class="flex-1 bg-surface-raised border border-amber-200 rounded-lg px-3 py-2 text-sm font-mono text-fg break-all select-all">{{ newlyCreatedKey }}</code>
              <button @click="copyKey(newlyCreatedKey)" class="flex-shrink-0 px-3 py-2 bg-amber-600 text-white text-xs font-medium rounded-lg hover:bg-amber-700 transition">
                {{ copied ? '已複製！' : '複製' }}
              </button>
            </div>
          </div>

          <!-- 現有 Keys 列表 -->
          <div>
            <h4 class="text-sm font-semibold text-fg-secondary mb-3">現有 API Keys</h4>
            <div v-if="apiKeysLoading" class="flex justify-center py-6">
              <SSpinner :size="24" />
            </div>
            <div v-else-if="apiKeys.length === 0" class="text-center py-6 text-fg-tertiary text-sm">
              尚無 API Keys，請點擊下方「建立新 Key」
            </div>
            <div v-else class="overflow-x-auto rounded-xl border border-neutral-200">
              <table class="min-w-full divide-y divide-gray-100">
                <thead class="bg-surface-sunken">
                  <tr>
                    <th class="px-4 py-2 text-left text-xs font-semibold text-fg-tertiary">名稱</th>
                    <th class="px-4 py-2 text-left text-xs font-semibold text-fg-tertiary">前綴</th>
                    <th class="px-4 py-2 text-left text-xs font-semibold text-fg-tertiary">狀態</th>
                    <th class="px-4 py-2 text-left text-xs font-semibold text-fg-tertiary">建立時間</th>
                    <th class="px-4 py-2 text-left text-xs font-semibold text-fg-tertiary">到期時間</th>
                    <th class="px-4 py-2 text-right text-xs font-semibold text-fg-tertiary">操作</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-100 bg-surface-raised">
                  <tr v-for="key in apiKeys" :key="key.id">
                    <td class="px-4 py-2.5 text-sm text-fg">{{ key.name }}</td>
                    <td class="px-4 py-2.5">
                      <code class="text-xs font-mono bg-neutral-100 px-2 py-0.5 rounded text-fg-secondary">{{ key.key_prefix }}…</code>
                    </td>
                    <td class="px-4 py-2.5">
                      <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold"
                            :class="key.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-neutral-100 text-fg-tertiary'">
                        {{ key.is_active ? '啟用' : '停用' }}
                      </span>
                    </td>
                    <td class="px-4 py-2.5 text-xs text-fg-tertiary">{{ formatDate(key.created_at) }}</td>
                    <td class="px-4 py-2.5 text-xs text-fg-tertiary">{{ key.expires_at ? formatDate(key.expires_at) : '永不到期' }}</td>
                    <td class="px-4 py-2.5 text-right">
                      <div class="flex justify-end gap-1">
                        <button @click="toggleKey(key)" class="text-xs px-2 py-1 rounded-lg transition"
                                :class="key.is_active ? 'text-fg-tertiary hover:text-amber-600 hover:bg-amber-50' : 'text-fg-tertiary hover:text-emerald-600 hover:bg-emerald-50'">
                          {{ key.is_active ? '停用' : '啟用' }}
                        </button>
                        <button @click="removeKey(key.id)" class="text-xs px-2 py-1 rounded-lg text-fg-tertiary hover:text-rose-600 hover:bg-rose-50 transition">
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
          <div class="border border-neutral-200 rounded-xl p-4 space-y-3">
            <h4 class="text-sm font-semibold text-fg-secondary">+ 建立新 Key</h4>
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

        <div class="px-6 pb-6 pt-4 border-t border-neutral-100 flex justify-end flex-shrink-0">
          <button @click="closeApiKeyDialog" class="px-4 py-2 border border-neutral-200 text-fg-secondary text-sm font-medium rounded-lg hover:bg-surface-sunken transition">關閉</button>
        </div>
      </div>
    </div>

    <!-- 建立/編輯應用 Dialog -->
    <div v-if="showDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div class="bg-surface-raised rounded-2xl shadow-2xl w-full max-w-xl overflow-hidden flex flex-col max-h-[90vh]">
        <div class="px-6 pt-6 pb-4 border-b border-neutral-100 flex-shrink-0">
          <h3 class="text-base font-semibold text-fg">{{ editingApp ? '編輯應用' : '新增 AI 應用' }}</h3>
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
            <div v-if="knowledgeBases.length === 0" class="text-xs text-fg-tertiary">
              尚無知識庫，請先在「知識庫管理」頁面建立
            </div>
            <div v-else class="flex flex-wrap gap-2 mt-1">
              <label
                v-for="kb in knowledgeBases"
                :key="kb.id"
                class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border cursor-pointer text-sm transition-all"
                :class="form.knowledge_base_ids.includes(kb.id)
                  ? 'border-indigo-400 bg-indigo-50 text-indigo-700'
                  : 'border-neutral-200 hover:border-neutral-300 text-fg-secondary'"
              >
                <input type="checkbox" :value="kb.id" v-model="form.knowledge_base_ids" class="hidden"/>
                <SIcon name="book-open" :size="14" />
                {{ kb.name }}
              </label>
            </div>
          </div>

          <!-- Reranker 設定 -->
          <div>
            <label class="form-label">Reranker 模型（選填）</label>
            <div v-if="rerankerModels.length === 0" class="text-xs text-fg-tertiary py-1">
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
            <label for="is_public" class="text-sm text-fg-secondary">公開應用（所有使用者可看到）</label>
          </div>
        </div>

        <div class="px-6 pb-6 pt-4 border-t border-neutral-100 flex justify-end gap-3 flex-shrink-0">
          <button @click="showDialog = false" class="px-4 py-2 border border-neutral-200 text-fg-secondary text-sm font-medium rounded-lg hover:bg-surface-sunken transition">取消</button>
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
  </div><!-- /flex h-full wrapper for sidebar + main -->
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
import EntityFolderSidebar from '../../components/common/EntityFolderSidebar.vue'
import { useProjectStore } from '../../stores/project'
import { SIcon, SSpinner } from '@staffkm/ui-kit'

const router = useRouter()
const auth = useAuthStore()

const loading = ref(false)
const saving = ref(false)
const applications = ref<Application[]>([])

// ── D-6：Project 過濾 + D-5 後續：Folder 過濾 ──────────────────────
const projects = useProjectStore()
const activeProject = computed(() => projects.active)
const activeFolderId = ref<string | null>(null)

const displayedApps = computed(() => {
  let list = applications.value
  if (activeProject.value) {
    const ids = new Set(activeProject.value.application_ids || [])
    list = list.filter(a => ids.has(a.id))
  }
  if (activeFolderId.value !== null) {
    list = list.filter(a => (a as any).folder_id === activeFolderId.value)
  }
  return list
})

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
    // 用 allSettled：任一 API 慢 / 503 不會卡住整個頁面渲染
    const [appsR, kbR, rerankerR] = await Promise.allSettled([
      applicationApi.list({ page_size: 50 }),
      http.get('/knowledge/bases', { params: { page_size: 50 } }),
      modelProviderApi.listModels(undefined, 'reranker'),
    ])
    if (appsR.status === 'fulfilled') {
      const v = appsR.value
      applications.value = v.data.data?.items ?? v.data.data ?? []
    } else {
      console.error('ApplicationListView apps load failed:', appsR.reason)
    }
    if (kbR.status === 'fulfilled') {
      const v = kbR.value
      knowledgeBases.value = v.data.data?.items ?? v.data.data ?? []
    } else {
      console.error('ApplicationListView kb load failed:', kbR.reason)
    }
    if (rerankerR.status === 'fulfilled') {
      const rerankerData = rerankerR.value.data.data
      rerankerModels.value = Array.isArray(rerankerData)
        ? rerankerData
        : (rerankerData?.items ?? [])
    } else {
      // reranker 失敗無傷大雅，只是進階設定的下拉空了
      console.warn('ApplicationListView reranker load failed:', rerankerR.reason)
    }
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
.form-label { @apply block text-xs font-semibold text-fg-secondary mb-1; }
.form-input { @apply w-full px-3 py-2 text-sm rounded-lg border border-neutral-200 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 outline-none transition; }
</style>
