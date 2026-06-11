<template>
  <aside class="w-60 border-r border-neutral-200 bg-surface-raised flex flex-col flex-shrink-0">
    <div class="px-3 py-3 border-b border-neutral-100 flex items-center justify-between">
      <h2 class="text-xs font-semibold uppercase tracking-widest text-neutral-500">
        資料夾
      </h2>
      <button
        @click="showNewFolder = true"
        class="w-6 h-6 flex items-center justify-center rounded-md text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700 transition"
        title="新增資料夾"
      >
        <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
        </svg>
      </button>
    </div>

    <nav class="flex-1 overflow-y-auto py-2 px-2">
      <!-- 根目錄 -->
      <button
        @click="$emit('update:activeFolderId', null)"
        class="w-full flex items-center gap-1 px-2 py-1.5 rounded-md text-sm transition-colors mb-0.5"
        :class="activeFolderId === null
          ? 'bg-neutral-100 text-neutral-900'
          : 'text-neutral-700 hover:bg-neutral-50'"
      >
        <span class="w-4 h-4"></span>
        <svg class="w-3.5 h-3.5 text-neutral-400" fill="currentColor" viewBox="0 0 24 24">
          <path d="M10 4H4a2 2 0 00-2 2v12a2 2 0 002 2h16a2 2 0 002-2V8a2 2 0 00-2-2h-8l-2-2z"/>
        </svg>
        <span class="truncate flex-1 text-left">{{ rootLabel }}</span>
      </button>

      <FolderTree
        :nodes="folderTreeData"
        :active-id="activeFolderId"
        @select="(n) => $emit('update:activeFolderId', n.id)"
      />
    </nav>

    <!-- 建立 folder modal -->
    <Teleport to="body">
      <div
        v-if="showNewFolder"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30"
        @click.self="showNewFolder = false"
      >
        <div class="w-full max-w-sm bg-surface-raised rounded-2xl shadow-2xl overflow-hidden">
          <div class="px-5 py-4 border-b border-neutral-100">
            <h3 class="text-sm font-semibold">新增資料夾</h3>
          </div>
          <div class="px-5 py-4">
            <input
              v-model="newName"
              placeholder="例：人事 / 採購 / 法規"
              class="w-full h-9 px-3 text-sm rounded-md border border-neutral-200 focus:outline-none focus:ring-1 focus:ring-brand-400"
              @keydown.enter="(e) => { if (!(e as any).isComposing) { onCreate() } }"
            />
            <p v-if="activeFolderId" class="text-[11px] text-neutral-500 mt-2">
              將建立於當前資料夾之下
            </p>
          </div>
          <div class="px-5 py-3 border-t border-neutral-100 bg-neutral-50 flex justify-end gap-2">
            <button @click="showNewFolder = false" class="h-9 px-4 text-sm rounded-lg border border-neutral-200">取消</button>
            <button :disabled="!newName.trim()" @click="onCreate" class="h-9 px-4 text-sm rounded-lg bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-40">建立</button>
          </div>
        </div>
      </div>
    </Teleport>
  </aside>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import FolderTree, { type FolderNode } from './FolderTree.vue'
import { entityFolderApi, type EntityFolder, type EntityKind } from '../../api/entityFolders'

const props = withDefaults(
  defineProps<{
    kind:           EntityKind
    activeFolderId: string | null
    rootLabel?:     string
  }>(),
  { rootLabel: '全部' },
)

defineEmits<{
  (e: 'update:activeFolderId', id: string | null): void
}>()

const folders = ref<EntityFolder[]>([])
const showNewFolder = ref(false)
const newName = ref('')

async function load() {
  try { folders.value = await entityFolderApi.list(props.kind) }
  catch (e) { console.warn('folder list failed:', e) }
}

async function onCreate() {
  const name = newName.value.trim()
  if (!name) return
  try {
    await entityFolderApi.create({
      entity_kind: props.kind,
      name,
      parent_id: props.activeFolderId,
    })
    newName.value = ''
    showNewFolder.value = false
    await load()
  } catch (e) {
    console.error('folder create failed:', e)
  }
}

const folderTreeData = computed<FolderNode[]>(() => {
  const map: Record<string, FolderNode> = {}
  for (const f of folders.value) {
    map[f.id] = { id: f.id, name: f.name, children: [] }
  }
  const roots: FolderNode[] = []
  for (const f of folders.value) {
    const node = map[f.id]
    if (f.parent_id && map[f.parent_id]) {
      map[f.parent_id].children!.push(node)
    } else {
      roots.push(node)
    }
  }
  return roots
})

onMounted(load)
</script>
