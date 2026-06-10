<template>
  <div class="flex flex-col h-full">
    <!-- 頁首 -->
    <div class="px-6 py-5 flex-shrink-0"><div class="card-hero flex items-center justify-between gap-4">
      <div>
        <h1 class="heading-page heading-accent">使用者管理</h1>
        <p class="text-sm text-fg-tertiary mt-0.5">新增 / 停用 / 改角色 / 重設密碼（共 {{ total }} 人）</p>
      </div>
      <div class="flex items-center gap-2">
        <div class="relative">
          <SIcon name="search" :size="14" class="absolute left-3 top-1/2 -translate-y-1/2 text-fg-tertiary" />
          <input
            v-model="search"
            @keyup.enter="reload"
            placeholder="搜尋使用者名稱 / email…"
            class="form-input h-9 pl-9 pr-3 w-72
                   focus:outline-none focus:ring-1 focus:ring-brand-400"
          />
        </div>
        <button
          @click="reload"
          class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50 flex items-center gap-1"
        >
          <SIcon name="refresh" :size="12" /> 重新整理
        </button>
        <button
          @click="openInvite"
          class="btn btn-primary text-xs"
        >
          <SIcon name="plus" :size="12" /> 邀請新成員
        </button>
      </div>
    </div>

    <!-- table -->
</div>
    <div class="flex-1 overflow-y-auto p-6">
      <AdminHelp title="使用者管理">
        <p>邀請成員、指派<strong class='text-fg'>角色</strong>（owner／admin／editor／viewer）、停用帳號。</p><p>角色決定能看／能改什麼；停用後該帳號<strong class='text-fg'>無法登入但資料保留</strong>，可隨時恢復。</p>
      </AdminHelp>
      <div v-if="loading" class="flex justify-center py-20">
        <SSpinner :size="24" />
      </div>

      <div v-else-if="!items.length" class="text-center py-20">
        <div class="w-12 h-12 bg-brand-50 rounded-2xl flex items-center justify-center mx-auto mb-3">
          <SIcon name="user" :size="24" :stroke-width="1.5" class="text-brand-500" />
        </div>
        <p class="text-fg-secondary font-medium">沒有使用者</p>
      </div>

      <table v-else class="w-full text-sm bg-surface-raised border border-bd rounded-2xl overflow-hidden shadow-sm">
        <thead>
          <tr class="bg-surface-sunken text-xs uppercase tracking-wider text-fg-tertiary text-left">
            <th class="px-4 py-3 font-semibold">使用者</th>
            <th class="px-4 py-3 font-semibold">Email</th>
            <th class="px-4 py-3 font-semibold">角色</th>
            <th class="px-4 py-3 font-semibold">狀態</th>
            <th class="px-4 py-3 font-semibold">建立時間</th>
            <th class="px-4 py-3 font-semibold text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in items" :key="u.id"
              class="border-t border-neutral-100 hover:bg-neutral-50/40 transition">
            <td class="px-4 py-3">
              <p class="font-medium text-fg text-sm">{{ formatUserName(u) }}</p>
              <p class="text-[10px] text-fg-tertiary font-mono mt-0.5">{{ u.username }}</p>
            </td>
            <td class="px-4 py-3 text-fg-secondary">{{ u.email || '—' }}</td>
            <td class="px-4 py-3">
              <span v-for="r in u.roles" :key="r"
                    class="inline-block mr-1 px-2 py-0.5 text-[10px] rounded-md font-medium"
                    :class="roleChipClass(r)">{{ r }}</span>
              <span v-if="!u.roles?.length" class="text-fg-tertiary text-xs">—</span>
            </td>
            <td class="px-4 py-3">
              <span class="px-2 py-0.5 text-[10px] rounded-md font-medium" :class="statusChipClass(u.status)">
                {{ statusLabel(u.status) }}
              </span>
            </td>
            <td class="px-4 py-3 text-xs text-fg-tertiary">{{ fmtDate(u.created_at) }}</td>
            <td class="px-4 py-3 text-right">
              <div class="inline-flex items-center gap-1">
                <button @click="openRole(u)" class="px-2 py-1 text-[11px] text-brand-700 bg-brand-50 hover:bg-brand-100 rounded">改角色</button>
                <button @click="openLoginMethods(u)" class="px-2 py-1 text-[11px] text-info-700 bg-info-50 hover:bg-info-100 rounded" title="限定登入方式（白名單）">登入方式</button>
                <button @click="openPassword(u)" class="px-2 py-1 text-[11px] text-fg-secondary bg-neutral-100 hover:bg-neutral-200 rounded">重設密碼</button>
                <button
                  @click="toggleStatus(u)"
                  class="px-2 py-1 text-[11px] rounded"
                  :class="u.status === 'active' ? 'text-warning-700 bg-warning-50 hover:bg-warning-100' : 'text-success-700 bg-success-50 hover:bg-success-100'"
                >{{ u.status === 'active' ? '停用' : '啟用' }}</button>
                <button @click="confirmDelete(u)" class="px-2 py-1 text-[11px] text-danger-700 bg-danger-50 hover:bg-danger-100 rounded">刪除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- 分頁 -->
      <div v-if="items.length" class="flex items-center justify-between mt-4 text-xs text-fg-tertiary">
        <span>第 {{ page }} / {{ totalPages }} 頁，共 {{ total }} 筆</span>
        <div class="flex gap-1">
          <button :disabled="page <= 1" @click="prevPage"
                  class="px-2 py-1 border border-neutral-200 rounded disabled:opacity-40">上一頁</button>
          <button :disabled="page >= totalPages" @click="nextPage"
                  class="px-2 py-1 border border-neutral-200 rounded disabled:opacity-40">下一頁</button>
        </div>
      </div>
    </div>

    <!-- 邀請新成員 -->
    <div v-if="inviting" class="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40" @click.self="inviting = false">
      <div class="card-warm shadow-xl w-full max-w-md p-5">
        <h3 class="text-base font-semibold text-fg">邀請新成員</h3>
        <div class="mt-4 space-y-3">
          <div>
            <label class="block text-xs text-fg-secondary mb-1">使用者名稱 *</label>
            <input v-model="inviteForm.username" class="form-input" @keyup.enter="submitInvite" />
          </div>
          <div>
            <label class="block text-xs text-fg-secondary mb-1">Email</label>
            <input v-model="inviteForm.email" type="email" class="form-input" />
          </div>
          <div>
            <label class="block text-xs text-fg-secondary mb-1">顯示名稱</label>
            <input v-model="inviteForm.display_name" class="form-input" />
          </div>
          <div>
            <label class="block text-xs text-fg-secondary mb-1">初始密碼 *（至少 8 字元）</label>
            <input v-model="inviteForm.password" type="text" class="w-full h-9 px-3 text-sm font-mono rounded-md border border-neutral-200 bg-surface-raised text-fg focus:outline-none focus:ring-1 focus:ring-brand-400" />
          </div>
          <div>
            <label class="block text-xs text-fg-secondary mb-1">角色</label>
            <select v-model="inviteForm.role" class="form-input">
              <option value="user">user</option>
              <option value="admin">admin</option>
              <option value="viewer">viewer</option>
            </select>
          </div>
        </div>
        <div class="mt-5 flex justify-end gap-2">
          <button @click="inviting = false" class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50">取消</button>
          <button @click="submitInvite" :disabled="saving" class="px-3 py-1.5 text-xs text-white bg-brand-600 hover:bg-brand-700 rounded-lg disabled:opacity-50">
            {{ saving ? '建立中…' : '建立' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 改角色 -->
    <div v-if="editingRole" class="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40" @click.self="editingRole = null">
      <div class="card-warm shadow-xl w-full max-w-sm p-5">
        <h3 class="text-base font-semibold text-fg">修改角色</h3>
        <p class="text-xs text-fg-tertiary mt-0.5">{{ editingRole.username }}</p>
        <div class="mt-4">
          <label class="block text-xs text-fg-secondary mb-1">角色</label>
          <select v-model="roleDraft" class="form-input">
            <option value="user">user</option>
            <option value="admin">admin</option>
            <option value="viewer">viewer</option>
          </select>
        </div>
        <div class="mt-5 flex justify-end gap-2">
          <button @click="editingRole = null" class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50">取消</button>
          <button @click="submitRole" :disabled="saving" class="px-3 py-1.5 text-xs text-white bg-brand-600 hover:bg-brand-700 rounded-lg disabled:opacity-50">儲存</button>
        </div>
      </div>
    </div>

    <!-- 重設密碼 -->
    <div v-if="editingPw" class="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40" @click.self="editingPw = null">
      <div class="card-warm shadow-xl w-full max-w-sm p-5">
        <h3 class="text-base font-semibold text-fg">重設密碼</h3>
        <p class="text-xs text-fg-tertiary mt-0.5">{{ editingPw.username }}</p>
        <div class="mt-4">
          <label class="block text-xs text-fg-secondary mb-1">新密碼（至少 8 字元）</label>
          <input v-model="pwDraft" type="text" class="w-full h-9 px-3 text-sm font-mono rounded-md border border-neutral-200 bg-surface-raised text-fg focus:outline-none focus:ring-1 focus:ring-brand-400" />
          <p class="text-[11px] text-warning-700 mt-2">請透過安全管道交給該使用者，並要求登入後立即更換。</p>
        </div>
        <div class="mt-5 flex justify-end gap-2">
          <button @click="editingPw = null" class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50">取消</button>
          <button @click="submitPw" :disabled="saving || pwDraft.length < 8" class="px-3 py-1.5 text-xs text-white bg-brand-600 hover:bg-brand-700 rounded-lg disabled:opacity-50">重設</button>
        </div>
      </div>
    </div>

    <!-- v2.7 X-Pack：登入方式白名單 -->
    <div v-if="editingMethods" class="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40" @click.self="editingMethods = null">
      <div class="card-warm shadow-xl w-full max-w-sm p-5">
        <h3 class="text-base font-semibold text-fg">限定登入方式</h3>
        <p class="text-xs text-fg-tertiary mt-0.5">{{ editingMethods.username }}</p>
        <p class="text-[11px] text-fg-tertiary mt-3">
          全部不勾 = 不限制（預設）；勾選後該使用者只能用勾選的方式登入。
        </p>
        <div class="mt-3 grid grid-cols-2 gap-2">
          <label v-for="m in METHODS" :key="m" class="flex items-center gap-2 text-sm text-fg-secondary cursor-pointer">
            <input type="checkbox" :value="m" v-model="methodsDraft" class="accent-brand-600" />
            <span>{{ m }}</span>
          </label>
        </div>
        <div class="mt-5 flex justify-end gap-2">
          <button @click="editingMethods = null" class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50">取消</button>
          <button @click="submitMethods" :disabled="saving" class="px-3 py-1.5 text-xs text-white bg-brand-600 hover:bg-brand-700 rounded-lg disabled:opacity-50">儲存</button>
        </div>
      </div>
    </div>

    <!-- 刪除確認 -->
    <div v-if="deleting" class="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40" @click.self="deleting = null">
      <div class="card-warm shadow-xl w-full max-w-sm p-5">
        <h3 class="text-base font-semibold text-fg">刪除使用者</h3>
        <p class="text-xs text-fg-secondary mt-2">確定要刪除「{{ deleting.username }}」？此操作為軟刪除，帳號會被停用且 username/email 會被釋放。</p>
        <div class="mt-5 flex justify-end gap-2">
          <button @click="deleting = null" class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-neutral-50">取消</button>
          <button @click="submitDelete" :disabled="saving" class="px-3 py-1.5 text-xs text-white bg-danger-600 hover:bg-danger-700 rounded-lg disabled:opacity-50">確認刪除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, computed, reactive } from 'vue'
import { SIcon, SSpinner } from '@staffkm/ui-kit'
import { usersApi, type User } from '../../api/users'
import { formatUserName } from '../../utils/userName'

const items = ref<User[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(true)
const saving = ref(false)
const search = ref('')

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

async function load() {
  loading.value = true
  try {
    const r = await usersApi.list(page.value, pageSize.value, search.value.trim())
    items.value = r.data || []
    total.value = r.meta?.total ?? 0
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '載入失敗')
  } finally {
    loading.value = false
  }
}

function reload() { page.value = 1; load() }
function prevPage() { if (page.value > 1) { page.value--; load() } }
function nextPage() { if (page.value < totalPages.value) { page.value++; load() } }

// 邀請
const inviting = ref(false)
const inviteForm = reactive({ username: '', email: '', display_name: '', password: '', role: 'user' })
function openInvite() {
  inviting.value = true
  inviteForm.username = ''
  inviteForm.email = ''
  inviteForm.display_name = ''
  inviteForm.password = ''
  inviteForm.role = 'user'
}
async function submitInvite() {
  if (!inviteForm.username || inviteForm.password.length < 8) {
    alert('請填寫使用者名稱與至少 8 字元的密碼')
    return
  }
  saving.value = true
  try {
    await usersApi.create({
      username: inviteForm.username,
      email: inviteForm.email || undefined,
      display_name: inviteForm.display_name || undefined,
      password: inviteForm.password,
      roles: [inviteForm.role],
    })
    inviting.value = false
    await load()
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '建立失敗')
  } finally {
    saving.value = false
  }
}

// 改角色
const editingRole = ref<User | null>(null)
const roleDraft = ref('user')
function openRole(u: User) {
  editingRole.value = u
  roleDraft.value = u.roles?.[0] || 'user'
}
async function submitRole() {
  if (!editingRole.value) return
  saving.value = true
  try {
    await usersApi.setRole(editingRole.value.id, [roleDraft.value])
    editingRole.value = null
    await load()
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '儲存失敗')
  } finally { saving.value = false }
}

// v2.7 X-Pack：登入方式白名單
const METHODS = ['password', 'oidc', 'google', 'github'] as const
const editingMethods = ref<User | null>(null)
const methodsDraft = ref<string[]>([])
function openLoginMethods(u: User) {
  editingMethods.value = u
  methodsDraft.value = Array.isArray(u.allowed_login_methods) ? [...u.allowed_login_methods] : []
}
async function submitMethods() {
  if (!editingMethods.value) return
  saving.value = true
  try {
    const payload = methodsDraft.value.length ? methodsDraft.value : null
    await usersApi.setLoginMethods(editingMethods.value.id, payload)
    editingMethods.value = null
    await load()
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '儲存失敗')
  } finally { saving.value = false }
}

// 重設密碼
const editingPw = ref<User | null>(null)
const pwDraft = ref('')
function openPassword(u: User) { editingPw.value = u; pwDraft.value = '' }
async function submitPw() {
  if (!editingPw.value || pwDraft.value.length < 8) return
  saving.value = true
  try {
    await usersApi.resetPassword(editingPw.value.id, pwDraft.value)
    editingPw.value = null
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '重設失敗')
  } finally { saving.value = false }
}

// 停用 / 啟用
async function toggleStatus(u: User) {
  const next = u.status === 'active' ? 'inactive' : 'active'
  try {
    await usersApi.setStatus(u.id, next as any)
    await load()
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '操作失敗')
  }
}

// 刪除
const deleting = ref<User | null>(null)
function confirmDelete(u: User) { deleting.value = u }
async function submitDelete() {
  if (!deleting.value) return
  saving.value = true
  try {
    await usersApi.delete(deleting.value.id)
    deleting.value = null
    await load()
  } catch (e: any) {
    alert(e?.response?.data?.detail || e?.message || '刪除失敗')
  } finally { saving.value = false }
}

// 顯示工具
function roleChipClass(r: string): string {
  if (r === 'admin')  return 'text-danger-700 bg-danger-50'
  if (r === 'viewer') return 'text-fg-secondary bg-neutral-100'
  return 'text-brand-700 bg-brand-50'
}
function statusChipClass(s: string): string {
  if (s === 'active')   return 'text-success-700 bg-success-50'
  if (s === 'locked')   return 'text-warning-700 bg-warning-50'
  return 'text-fg-secondary bg-neutral-100'
}
function statusLabel(s: string): string {
  if (s === 'active')   return '啟用中'
  if (s === 'locked')   return '已鎖定'
  return '已停用'
}
function fmtDate(s?: string | null): string {
  if (!s) return '—'
  try { return new Date(s).toLocaleString('zh-TW', { hour12: false }) } catch { return s }
}

onMounted(load)
</script>
