<template>
  <div class="flex flex-col h-full overflow-hidden" style="background:#f0f2f5;">

    <!-- ── 頂部工具列 ──────────────────────────────────────────────────────── -->
    <div class="h-12 bg-surface-raised border-b border-neutral-200 px-4 flex items-center justify-between flex-shrink-0 shadow-sm">
      <div class="flex items-center gap-3">
        <button @click="router.push('/applications')"
                class="p-1.5 rounded-lg text-fg-tertiary hover:text-fg-secondary hover:bg-neutral-100 transition">
          <SIcon name="chevron-left" :size="16" />
        </button>
        <div>
          <span class="text-sm font-semibold text-fg">工作流程編輯器</span>
          <span class="ml-2 text-xs text-fg-tertiary font-mono">{{ appId }}</span>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <!-- Undo / Redo (M2 收尾) -->
        <button @click="onUndo" :disabled="!canUndo"
                class="px-2.5 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:border-indigo-400 hover:text-indigo-600 transition disabled:opacity-40"
                title="復原（Cmd/Ctrl+Z）"
                aria-label="復原（Cmd/Ctrl+Z）">↶</button>
        <button @click="onRedo" :disabled="!canRedo"
                class="px-2.5 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:border-indigo-400 hover:text-indigo-600 transition disabled:opacity-40"
                title="重做（Cmd/Ctrl+Shift+Z）"
                aria-label="重做（Cmd/Ctrl+Shift+Z）">↷</button>
        <span class="text-[11px] text-fg-tertiary px-1 tabular-nums" :title="`縮放 ${zoomPct}%`">{{ zoomPct }}%</span>
        <span class="w-px h-5 bg-gray-200 mx-1"></span>
        <!-- 自動排版 -->
        <button @click="autoLayout"
                class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:border-indigo-400 hover:text-indigo-600 transition">
          自動排版
        </button>
        <!-- 歷史版本 (D-7) -->
        <button @click="openHistory"
                class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:border-indigo-400 hover:text-indigo-600 transition"
                :class="showHistory ? 'border-indigo-400 text-indigo-600 bg-indigo-50' : ''">
          歷史版本
        </button>
        <!-- 測試 -->
        <button @click="showTest = !showTest"
                class="px-3 py-1.5 text-xs text-fg-secondary bg-surface-raised border border-neutral-200 rounded-lg hover:border-indigo-400 hover:text-indigo-600 transition"
                :class="showTest ? 'border-indigo-400 text-indigo-600 bg-indigo-50' : ''">
          ▶ 測試
        </button>
        <!-- 儲存 -->
        <button @click="saveWorkflow" :disabled="saving"
                class="px-4 py-1.5 bg-indigo-600 text-white text-xs font-semibold rounded-lg hover:bg-indigo-700 transition disabled:opacity-50">
          {{ saving ? '儲存中…' : '儲存流程' }}
        </button>
      </div>
    </div>

    <!-- ── 主體三欄 ──────────────────────────────────────────────────────── -->
    <div class="flex-1 flex overflow-hidden">

      <!-- 左欄：節點 Palette ─────────────────────────────────────────────── -->
      <div class="w-48 flex-shrink-0 bg-surface-raised border-r border-neutral-200 flex flex-col overflow-hidden shadow-sm">
        <div class="px-3 py-2.5 border-b border-neutral-100">
          <span class="text-[11px] font-bold text-fg-tertiary uppercase tracking-wider">節點類型</span>
        </div>
        <div class="flex-1 overflow-y-auto py-2">
          <template v-for="group in PALETTE_GROUPS" :key="group.label">
            <div class="px-3 pt-3 pb-1">
              <span class="text-[10px] font-semibold text-fg-tertiary uppercase tracking-wider">{{ group.label }}</span>
            </div>
            <div v-for="nodeType in group.items" :key="nodeType"
                 class="mx-2 mb-0.5 flex items-center gap-2 px-3 py-2 rounded-lg text-xs cursor-grab select-none transition
                        text-fg-secondary hover:bg-indigo-50 hover:text-indigo-700 active:scale-95"
                 @mousedown="paletteDragStart($event, nodeType)">
              <span class="text-sm flex-shrink-0">{{ NODE_META[nodeType].icon }}</span>
              <span class="font-medium truncate">{{ NODE_META[nodeType].label }}</span>
            </div>
          </template>
        </div>
        <div class="px-3 py-2.5 border-t border-neutral-100 text-[10px] text-fg-tertiary text-center">
          拖曳節點到畫布
        </div>
      </div>

      <!-- 中欄：LogicFlow 畫布 ──────────────────────────────────────────── -->
      <div class="flex-1 relative overflow-hidden">
        <div ref="canvasRef" class="w-full h-full" />

        <!-- 無節點提示 -->
        <div v-if="nodeCount === 0"
             class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <div class="text-xs uppercase tracking-widest text-neutral-400 mb-2 opacity-60">空白畫布</div>
          <p class="text-sm text-fg-tertiary opacity-60">從左側拖曳節點到畫布開始建立工作流程</p>
        </div>

        <!-- 縮放提示（右下） -->
        <div class="absolute bottom-4 right-4 flex flex-col gap-1 z-10">
          <button @click="lfZoom(1.2)" class="lf-ctrl-btn" title="放大">+</button>
          <button @click="lfZoom(0.8)" class="lf-ctrl-btn" title="縮小">−</button>
          <button @click="lfFit" class="lf-ctrl-btn" title="適合畫面">⊡</button>
        </div>
      </div>

      <!-- 右欄：節點設定面板 ──────────────────────────────────────────────── -->
      <transition
        enter-active-class="transition-all duration-200 ease-out"
        enter-from-class="opacity-0 translate-x-4"
        enter-to-class="opacity-100 translate-x-0"
        leave-active-class="transition-all duration-150 ease-in"
        leave-from-class="opacity-100 translate-x-0"
        leave-to-class="opacity-0 translate-x-4"
      >
        <div v-if="selectedNode"
             class="w-80 flex-shrink-0 bg-surface-raised border-l border-neutral-200 flex flex-col overflow-hidden shadow-sm">
          <NodeConfigPanel
            :node="selectedNode"
            @close="deselectNode"
            @delete="deleteSelectedNode"
          />
        </div>
      </transition>

    </div><!-- /三欄 -->

    <!-- ── 測試面板（底部滑出）──────────────────────────────────────────── -->
    <transition
      enter-active-class="transition-all duration-200 ease-out"
      enter-from-class="opacity-0 translate-y-4"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition-all duration-150 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 translate-y-4"
    >
      <div v-if="showTest"
           class="h-72 flex-shrink-0 bg-surface-raised border-t border-neutral-200 flex flex-col shadow-lg">
        <div class="px-5 py-3 border-b border-neutral-100 flex items-center justify-between flex-shrink-0">
          <span class="text-sm font-semibold text-fg-secondary">工作流程測試</span>
          <button @click="showTest = false" class="text-fg-tertiary hover:text-fg-secondary">×</button>
        </div>
        <div class="flex-1 flex overflow-hidden">
          <!-- 輸入 -->
          <div class="w-72 flex-shrink-0 border-r border-neutral-100 p-4 flex flex-col gap-3">
            <textarea v-model="testInput" rows="4"
                      class="flex-1 resize-none text-sm border border-neutral-200 rounded-xl px-3 py-2.5 focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
                      placeholder="輸入測試問題…"/>
            <button @click="runTest" :disabled="testRunning"
                    class="py-2 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-700 transition disabled:opacity-50">
              {{ testRunning ? '執行中…' : '▶ 執行測試' }}
            </button>
          </div>
          <!-- 輸出 -->
          <div class="flex-1 overflow-y-auto p-4">
            <div v-if="testEvents.length === 0" class="text-sm text-fg-tertiary">等待執行…</div>
            <div v-for="(ev, i) in testEvents" :key="i" class="mb-2">
              <span class="inline-block px-2 py-0.5 rounded-full text-[11px] font-semibold mr-2"
                    :class="evChipClass(ev.event)">{{ ev.event }}</span>
              <span class="text-sm text-fg whitespace-pre-wrap">{{ ev.data }}</span>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- ── 歷史版本抽屜 (D-7 後續) ─────────────────────────────────────── -->
    <Teleport to="body">
      <transition
        enter-active-class="transition-all duration-200 ease-out"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition-all duration-150 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div v-if="showHistory" class="fixed inset-0 z-50 bg-black/30" @click.self="showHistory = false">
          <transition
            enter-active-class="transition-transform duration-200 ease-out"
            enter-from-class="translate-x-full"
            enter-to-class="translate-x-0"
            leave-active-class="transition-transform duration-150 ease-in"
            leave-from-class="translate-x-0"
            leave-to-class="translate-x-full"
            appear
          >
            <aside class="absolute right-0 top-0 bottom-0 w-96 bg-surface-raised shadow-2xl flex flex-col">
              <div class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between flex-shrink-0">
                <div>
                  <h3 class="text-sm font-semibold text-fg">歷史版本</h3>
                  <p class="text-[11px] text-fg-tertiary mt-0.5">每次儲存後可手動建立快照</p>
                </div>
                <button @click="showHistory = false" class="text-fg-tertiary hover:text-fg-secondary">
                  <SIcon name="x" :size="16" />
                </button>
              </div>

              <div class="px-5 py-3 border-b border-neutral-100 bg-neutral-50 flex-shrink-0">
                <div class="flex items-center gap-2">
                  <input v-model="snapshotNote" placeholder="版本說明（選填）"
                         class="flex-1 h-8 px-2 text-xs rounded-md border border-neutral-200 focus:outline-none focus:ring-1 focus:ring-indigo-400" />
                  <button @click="onSnapshot" :disabled="snapshotBusy"
                          class="h-8 px-3 text-xs rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-40">
                    {{ snapshotBusy ? '建立中…' : '建立快照' }}
                  </button>
                </div>
              </div>

              <div class="flex-1 overflow-y-auto px-3 py-2">
                <p v-if="historyLoading" class="text-xs text-neutral-400 text-center py-8">載入中…</p>
                <p v-else-if="!versions.length" class="text-xs text-neutral-400 text-center py-8">尚無歷史版本</p>
                <ul v-else class="space-y-1">
                  <li v-for="v in versions" :key="v.id"
                      class="p-3 rounded-lg border border-neutral-100 hover:border-indigo-200 hover:bg-indigo-50/40 transition">
                    <div class="flex items-center justify-between">
                      <span class="text-xs font-semibold text-fg">v{{ v.version_number }}</span>
                      <button @click="onRestore(v.version_number)" :disabled="restoreBusy === v.version_number"
                              class="text-[11px] text-indigo-600 hover:text-indigo-800 disabled:opacity-40">
                        {{ restoreBusy === v.version_number ? '回滾中…' : '回滾此版本' }}
                      </button>
                    </div>
                    <p v-if="v.note" class="text-[11px] text-fg-secondary mt-1 line-clamp-2">{{ v.note }}</p>
                    <p class="text-[10px] text-fg-tertiary mt-1 font-mono">{{ formatTime(v.created_at) }}</p>
                  </li>
                </ul>
              </div>
            </aside>
          </transition>
        </div>
      </transition>
    </Teleport>

  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LogicFlow from '@logicflow/core'
import '@logicflow/core/dist/style/index.css'

import { registerWorkflowNodes, NODE_META, PALETTE_GROUPS, getDefaultConfig } from '../../components/workflow/lf-nodes'
import NodeConfigPanel from '../../components/workflow/NodeConfigPanel.vue'
import { workflowApi, type WorkflowNode, type WorkflowEdge } from '../../api/workflow'
import { appVersionApi, type AppVersion } from '../../api/application'
import { SIcon } from '@staffkm/ui-kit'

// ─── 路由 ──────────────────────────────────────────────────────────────────────
const route  = useRoute()
const router = useRouter()
const appId  = route.params.appId as string

// ─── 狀態 ──────────────────────────────────────────────────────────────────────
const canvasRef    = ref<HTMLElement | null>(null)
const saving       = ref(false)
const showTest     = ref(false)
const testInput    = ref('')
const testRunning  = ref(false)
const testEvents   = ref<{ event: string; data: string }[]>([])
const nodeCount    = ref(0)

// ─── M2 收尾：undo/redo / zoom / 剪貼簿 ──────────────────────────────
const canUndo   = ref(false)
const canRedo   = ref(false)
const zoomPct   = ref(100)
const clipboardNode = ref<any | null>(null)
const GRID = 20  // snap-to-grid 格距

function refreshHistoryState() {
  try {
    const hist = (lf as any)?.history
    canUndo.value = !!hist?.undoAble
    canRedo.value = !!hist?.redoAble
  } catch { /* noop */ }
}
function onUndo() { lf?.undo?.(); refreshHistoryState(); countNodes() }
function onRedo() { lf?.redo?.(); refreshHistoryState(); countNodes() }
function snapToGrid(p: number) { return Math.round(p / GRID) * GRID }

// ─── 歷史版本抽屜 (D-7 後續) ────────────────────────────────────────────
const showHistory   = ref(false)
const historyLoading = ref(false)
const versions      = ref<AppVersion[]>([])
const snapshotNote  = ref('')
const snapshotBusy  = ref(false)
const restoreBusy   = ref<number | null>(null)

async function loadVersions() {
  historyLoading.value = true
  try { versions.value = await appVersionApi.list(appId) }
  catch (e) { console.warn('versions load failed:', e) }
  finally { historyLoading.value = false }
}
function openHistory() {
  showHistory.value = true
  loadVersions()
}
async function onSnapshot() {
  snapshotBusy.value = true
  try {
    await appVersionApi.create(appId, snapshotNote.value.trim() || undefined)
    snapshotNote.value = ''
    await loadVersions()
  } catch (e: any) {
    alert('建立快照失敗：' + (e?.message || e))
  } finally {
    snapshotBusy.value = false
  }
}
async function onRestore(versionNumber: number) {
  if (!confirm(`確定要回滾到 v${versionNumber}？當前設定會自動建立快照保留 audit。`)) return
  restoreBusy.value = versionNumber
  try {
    await appVersionApi.restore(appId, versionNumber)
    await loadVersions()
    alert(`已回滾至 v${versionNumber}，請重新整理頁面以套用。`)
  } catch (e: any) {
    alert('回滾失敗：' + (e?.message || e))
  } finally {
    restoreBusy.value = null
  }
}
function formatTime(s: string) {
  try { return new Date(s).toLocaleString('zh-TW', { hour12: false }) }
  catch { return s }
}

// 選取的節點（雙向綁定 LF ← → Vue）
const selectedNode = ref<{
  id: string
  node_key: string
  node_type: string
  label: string
  config: Record<string, any>
} | null>(null)

// ─── LogicFlow 實例 ────────────────────────────────────────────────────────────
let lf: LogicFlow | null = null

onMounted(async () => {
  if (!canvasRef.value) return

  lf = new LogicFlow({
    container: canvasRef.value,
    grid: {
      visible: true,
      type: 'dot',
      config: { color: '#D1D5DB', size: 2 },
    },
    background: { color: '#F0F2F5' },
    edgeType: 'polyline',
    adjustEdge: true,
    keyboard: { enabled: true },
    isSilentMode: false,
  })

  registerWorkflowNodes(lf)

  // 節點點擊 → 顯示設定面板
  lf.on('node:click', ({ data }: any) => {
    const props = data.properties || {}
    selectedNode.value = {
      id:        data.id,
      node_key:  props.node_key || data.id,
      node_type: data.type,
      label:     props.label || '',
      config:    props.config ? JSON.parse(JSON.stringify(props.config)) : getDefaultConfig(data.type),
    }
  })

  // 點空白區域 → 取消選取
  lf.on('blank:click', () => deselectNode())

  // 刪除節點時同步清空面板
  lf.on('node:delete', ({ data }: any) => {
    if (selectedNode.value?.id === data.id) deselectNode()
    countNodes()
  })

  // 新增節點時更新計數
  lf.on('node:add', () => { countNodes(); refreshHistoryState() })

  // M2 收尾：snap-to-grid（拖曳停止後自動對齊網格）
  lf.on('node:drag-stop', ({ data }: any) => {
    const model = (lf!.graphModel as any).getNodeModelById(data.id)
    if (!model) return
    const nx = snapToGrid(model.x)
    const ny = snapToGrid(model.y)
    if (nx !== model.x || ny !== model.y) model.moveTo(nx, ny)
    refreshHistoryState()
  })

  // M2 收尾：history / zoom 變化追蹤
  lf.on('history:change', refreshHistoryState)
  lf.on('graph:transform', ({ transform }: any) => {
    if (transform?.SCALE_X) zoomPct.value = Math.round(transform.SCALE_X * 100)
  })

  // 條件節點連線自動加上 True/False 標籤
  lf.on('edge:add', ({ data }: any) => {
    const sourceModel = (lf!.graphModel as any).getNodeModelById(data.sourceNodeId)
    if (sourceModel?.type !== 'condition') return
    const anchorId = data.sourceAnchorId || ''
    const branchType = anchorId.endsWith('_true') ? 'true' : anchorId.endsWith('_false') ? 'false' : null
    if (!branchType) return
    const label = branchType === 'true' ? 'True' : 'False'
    const edgeModel = (lf!.graphModel as any).getEdgeModelById(data.id)
    if (edgeModel) {
      edgeModel.setProperties({ branchType })
      edgeModel.setText({ value: label })
    }
  })

  lf.render({})
  await loadWorkflow()
  countNodes()
  refreshHistoryState()

  // M2 收尾：全域鍵盤快捷鍵
  window.addEventListener('keydown', onKeydown)
})

function onKeydown(e: KeyboardEvent) {
  // 避免在輸入框 / textarea 內攔截
  const tag = (e.target as HTMLElement)?.tagName?.toLowerCase()
  if (tag === 'input' || tag === 'textarea' || (e.target as HTMLElement)?.isContentEditable) return

  const meta = e.metaKey || e.ctrlKey
  if (meta && e.key.toLowerCase() === 's') {
    e.preventDefault()
    saveWorkflow()
  } else if (meta && e.key.toLowerCase() === 'z' && !e.shiftKey) {
    e.preventDefault(); onUndo()
  } else if (meta && (e.key.toLowerCase() === 'y' || (e.shiftKey && e.key.toLowerCase() === 'z'))) {
    e.preventDefault(); onRedo()
  } else if (meta && e.key.toLowerCase() === 'c' && selectedNode.value) {
    clipboardNode.value = JSON.parse(JSON.stringify(selectedNode.value))
  } else if (meta && e.key.toLowerCase() === 'v' && clipboardNode.value) {
    e.preventDefault(); pasteClipboard()
  } else if ((e.key === 'Delete' || e.key === 'Backspace') && selectedNode.value) {
    e.preventDefault(); deleteSelectedNode()
  }
}

function pasteClipboard() {
  if (!lf || !clipboardNode.value) return
  const src = clipboardNode.value
  const sm = (lf.graphModel as any).getNodeModelById(src.id)
  const baseX = sm?.x ?? 200
  const baseY = sm?.y ?? 200
  lf.addNode({
    type: src.node_type,
    x: snapToGrid(baseX + 40),
    y: snapToGrid(baseY + 40),
    properties: {
      node_key: `${src.node_type}_${Date.now()}`,
      label:    src.label || '',
      config:   JSON.parse(JSON.stringify(src.config || {})),
    },
  } as any)
  refreshHistoryState()
}

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  lf?.destroy?.()
  lf = null
})

// ─── 工具函式 ──────────────────────────────────────────────────────────────────
function countNodes() {
  nodeCount.value = (lf?.graphModel as any)?.nodes?.length ?? 0
}

function deselectNode() {
  selectedNode.value = null
}

function deleteSelectedNode() {
  if (!selectedNode.value || !lf) return
  lf.deleteNode(selectedNode.value.id)
  deselectNode()
  countNodes()
}

// 畫布縮放
function lfZoom(ratio: number) {
  lf?.zoom(ratio)
}
function lfFit() {
  lf?.fitView()
}

// 自動排版（waterfall layout）
function autoLayout() {
  if (!lf) return
  const nodes = (lf.graphModel as any).nodes as any[]
  if (!nodes.length) return
  const cols = 3
  const xGap = 240, yGap = 140, startX = 200, startY = 100
  nodes.forEach((n, i) => {
    const col = i % cols, row = Math.floor(i / cols)
    n.moveTo(startX + col * xGap, startY + row * yGap)
  })
  lf.fitView()
}

// ─── Palette 拖入 ──────────────────────────────────────────────────────────────
function paletteDragStart(event: MouseEvent, nodeType: string) {
  if (!lf) return
  lf.dnd.startDrag({
    type: nodeType,
    properties: {
      node_key: `${nodeType}_${Date.now()}`,
      label:    '',
      config:   getDefaultConfig(nodeType),
    },
    text: { value: '' },
  })
}

// ─── 選取節點 → 同步回 LogicFlow ─────────────────────────────────────────────
// 當 config panel 的值改變時，把新值寫回 LF node model，觸發重繪
watch(
  selectedNode,
  (node) => {
    if (!node || !lf) return
    const model = (lf.graphModel as any).getNodeModelById(node.id)
    if (!model) return
    model.setProperties({
      node_key: node.node_key,
      label:    node.label,
      config:   node.config,
    })
  },
  { deep: true },
)

// ─── 資料轉換：API ↔ LogicFlow ────────────────────────────────────────────────
function apiToLf(data: { nodes: WorkflowNode[]; edges: WorkflowEdge[] }) {
  const keyToId: Record<string, string> = {}

  const lfNodes = data.nodes.map((n) => {
    keyToId[n.node_key] = n.id
    return {
      id:   n.id,
      type: n.node_type,
      x:    n.position?.x ?? 200,
      y:    n.position?.y ?? 200,
      properties: {
        node_key: n.node_key,
        label:    n.label || '',
        config:   n.config || {},
      },
      text: { value: '' },
    }
  })

  const lfEdges = data.edges.map((e) => {
    const sourceId   = keyToId[e.source_node_key] || e.source_node_key
    const targetId   = keyToId[e.target_node_key] || e.target_node_key
    const branchType = (e.condition as any)?.branch as string | undefined
    const edge: any  = {
      id:           e.id,
      type:         'polyline',
      sourceNodeId: sourceId,
      targetNodeId: targetId,
      properties:   { branchType, condition: e.condition },
    }
    if (branchType === 'true')  edge.sourceAnchorId = `${sourceId}_true`
    if (branchType === 'false') edge.sourceAnchorId = `${sourceId}_false`
    if (branchType)             edge.text = { value: branchType === 'true' ? 'True' : 'False' }
    return edge
  })

  return { nodes: lfNodes, edges: lfEdges }
}

function lfToApi(): { nodes: WorkflowNode[]; edges: WorkflowEdge[] } {
  if (!lf) return { nodes: [], edges: [] }
  const graphData = lf.getGraphData() as any
  const idToKey: Record<string, string> = {}

  const nodes: WorkflowNode[] = (graphData.nodes || []).map((n: any) => {
    const key = n.properties?.node_key || n.id
    idToKey[n.id] = key
    return {
      id:        n.id,
      node_key:  key,
      node_type: n.type,
      label:     n.properties?.label || '',
      config:    n.properties?.config || {},
      position:  { x: Math.round(n.x), y: Math.round(n.y) },
    }
  })

  const edges: WorkflowEdge[] = (graphData.edges || []).map((e: any) => {
    // 從 sourceAnchorId 或 properties 推斷 branchType
    let branchType = e.properties?.branchType
    if (!branchType) {
      if (e.sourceAnchorId?.endsWith('_true'))  branchType = 'true'
      if (e.sourceAnchorId?.endsWith('_false')) branchType = 'false'
    }
    return {
      id:               e.id,
      source_node_key:  idToKey[e.sourceNodeId] || e.sourceNodeId,
      target_node_key:  idToKey[e.targetNodeId] || e.targetNodeId,
      condition:        branchType ? { branch: branchType } : undefined,
    }
  })

  return { nodes, edges }
}

// ─── 載入 / 儲存 ───────────────────────────────────────────────────────────────
async function loadWorkflow() {
  try {
    const res = await workflowApi.get(appId)
    const raw = res.data?.data?.data
    if (!raw?.nodes?.length) return
    const lfData = apiToLf(raw)
    lf!.render(lfData)
    await nextTick()
    lf!.fitView()
    countNodes()
  } catch { /* 新工作流程，畫布保持空白 */ }
}

async function saveWorkflow() {
  if (!lf) return
  saving.value = true
  try {
    const payload = lfToApi()
    await workflowApi.save(appId, payload)
  } finally {
    saving.value = false
  }
}

// ─── 測試執行 ──────────────────────────────────────────────────────────────────
async function runTest() {
  if (testRunning.value || !testInput.value.trim()) return
  testRunning.value = true
  testEvents.value  = []

  try {
    const response = await fetch(workflowApi.chatUrl(appId), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        Accept: 'text/event-stream',
      },
      body: JSON.stringify({
        messages: [{ role: 'user', content: testInput.value.trim() }],
      }),
    })

    if (!response.body) throw new Error('無回應串流')
    const reader  = response.body.getReader()
    const decoder = new TextDecoder()
    let buf = '', pendingEvent = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const lines = buf.split('\n')
      buf = lines.pop() ?? ''

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          pendingEvent = line.slice(7).trim()
        } else if (line.startsWith('data: ') && pendingEvent) {
          testEvents.value.push({ event: pendingEvent, data: line.slice(6) })
          pendingEvent = ''
        } else if (line === '') {
          pendingEvent = ''
        }
      }
    }
  } catch (e: any) {
    testEvents.value.push({ event: 'error', data: e.message })
  } finally {
    testRunning.value = false
  }
}

function evChipClass(event: string) {
  const map: Record<string, string> = {
    node_start: 'bg-blue-100 text-blue-700',
    node_end:   'bg-green-100 text-green-700',
    token:      'bg-neutral-100 text-fg-secondary',
    citations:  'bg-amber-100 text-amber-700',
    error:      'bg-red-100 text-red-700',
    form_request:'bg-indigo-100 text-indigo-700',
  }
  return map[event] ?? 'bg-neutral-100 text-fg-tertiary'
}
</script>

<style scoped>
.lf-ctrl-btn {
  @apply w-8 h-8 flex items-center justify-center bg-surface-raised border border-neutral-200 rounded-lg
         text-fg-secondary text-sm font-mono hover:border-indigo-400 hover:text-indigo-600
         shadow-sm transition cursor-pointer;
}
</style>
