<template>
  <Teleport to="body">
    <transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0"
      leave-active-class="transition duration-150 ease-in"
      leave-to-class="opacity-0"
    >
      <div v-if="open" class="fixed inset-0 z-40 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm"
           @click.self="close">
        <transition
          enter-active-class="transition duration-200 ease-out"
          enter-from-class="opacity-0 scale-95 translate-y-2"
          leave-active-class="transition duration-150 ease-in"
          leave-to-class="opacity-0 scale-95"
          appear
        >
          <div v-if="open" class="w-full max-w-md bg-surface-raised rounded-2xl shadow-2xl overflow-hidden">
            <!-- header -->
            <div class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between">
              <h2 class="text-base font-semibold text-fg">建立新工作區</h2>
              <button @click="close" class="p-1 rounded-md text-fg-tertiary hover:text-fg-secondary hover:bg-neutral-100 transition">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>

            <!-- form -->
            <form @submit.prevent="onSubmit" class="px-5 py-4 space-y-4">
              <div>
                <label class="block text-xs font-semibold text-fg-secondary mb-1">
                  工作區名稱 <span class="text-rose-500">*</span>
                </label>
                <input
                  ref="nameInput"
                  v-model="form.name"
                  required maxlength="128"
                  placeholder="例：工程部、人事處、法規科"
                  class="w-full text-sm border border-neutral-200 rounded-lg px-3 py-2 focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
                />
              </div>

              <div>
                <label class="block text-xs font-semibold text-fg-secondary mb-1">
                  Slug（URL 識別子）<span class="text-rose-500">*</span>
                </label>
                <input
                  v-model="form.slug"
                  required pattern="^[a-z0-9][a-z0-9-]*[a-z0-9]$"
                  minlength="2" maxlength="64"
                  placeholder="engineering / hr-dept / legal-team"
                  class="w-full text-sm font-mono border border-neutral-200 rounded-lg px-3 py-2 focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
                />
                <p class="text-[11px] text-fg-tertiary mt-1">小寫英數字 + 連字號，不可開頭/結尾用連字號</p>
              </div>

              <div>
                <label class="block text-xs font-semibold text-fg-secondary mb-1">說明（選填）</label>
                <textarea
                  v-model="form.description"
                  maxlength="512" rows="3"
                  placeholder="這個工作區的用途、成員範圍等"
                  class="w-full text-sm border border-neutral-200 rounded-lg px-3 py-2 focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 resize-none"
                ></textarea>
              </div>

              <p v-if="error" class="text-xs text-rose-600 bg-rose-50 border border-rose-100 rounded-lg px-3 py-2">
                {{ error }}
              </p>
            </form>

            <!-- footer -->
            <div class="px-5 py-3 border-t border-neutral-100 flex items-center justify-end gap-2 bg-surface-sunken">
              <button
                @click="close"
                class="px-4 py-2 text-sm text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:bg-surface-sunken transition"
              >取消</button>
              <button
                @click="onSubmit"
                :disabled="!canSubmit || submitting"
                class="px-4 py-2 text-sm text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                {{ submitting ? '建立中…' : '建立' }}
              </button>
            </div>
          </div>
        </transition>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'

import { useWorkspaceStore } from '../../stores/workspace'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{
  'update:open': [v: boolean]
  created: [id: string]
}>()

const store = useWorkspaceStore()
const nameInput = ref<HTMLInputElement | null>(null)

const form = ref({ name: '', slug: '', description: '' })
const error = ref<string | null>(null)
const submitting = ref(false)

const canSubmit = computed(
  () => form.value.name.trim().length > 0 && /^[a-z0-9][a-z0-9-]*[a-z0-9]$/.test(form.value.slug),
)

// 自動從 name 推 slug（中→拼音替代不做、保留英數）
watch(() => form.value.name, (v) => {
  // 只在使用者還沒手動編輯 slug 時自動生成
  if (form.value.slug === '' || form.value.slug === lastAutoSlug.value) {
    const auto = v.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 64)
    form.value.slug = auto
    lastAutoSlug.value = auto
  }
})
const lastAutoSlug = ref('')

watch(() => props.open, async (open) => {
  if (open) {
    form.value = { name: '', slug: '', description: '' }
    error.value = null
    await nextTick()
    nameInput.value?.focus()
  }
})

function close() {
  if (submitting.value) return
  emit('update:open', false)
}

async function onSubmit() {
  if (!canSubmit.value || submitting.value) return
  submitting.value = true
  error.value = null
  try {
    const ws = await store.createAndSwitch({
      name: form.value.name.trim(),
      slug: form.value.slug,
      description: form.value.description.trim() || undefined,
    })
    emit('created', ws.id)
    emit('update:open', false)
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    error.value =
      typeof detail === 'string'
        ? detail
        : detail?.[0]?.msg || e.message || '建立失敗'
  } finally {
    submitting.value = false
  }
}
</script>
