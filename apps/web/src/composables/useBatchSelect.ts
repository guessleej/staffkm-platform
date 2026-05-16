/**
 * useBatchSelect — 通用「批量選擇」狀態管理。
 *
 * 任何列表元件（KB 列表 / Application 列表 / 文件列表 / Tool 列表…）
 * 都可呼叫此 composable，得到一致的 selection API + toolbar 狀態。
 *
 * 用法：
 *   const { selected, isSelected, toggle, clear, selectAll, count, hasSelection }
 *     = useBatchSelect()
 *
 *   <BatchSelectToolbar :count="count" @clear="clear">
 *     <button>移至…</button>
 *     <button>刪除</button>
 *   </BatchSelectToolbar>
 */
import { computed, ref } from 'vue'

export interface UseBatchSelectReturn {
  selected:     ReturnType<typeof ref<Set<string>>>
  count:        ReturnType<typeof computed<number>>
  hasSelection: ReturnType<typeof computed<boolean>>
  isSelected:   (id: string) => boolean
  toggle:       (id: string) => void
  selectAll:    (ids: string[]) => void
  clear:        () => void
  invert:       (allIds: string[]) => void
}

export function useBatchSelect(): UseBatchSelectReturn {
  const selected = ref<Set<string>>(new Set())

  const count        = computed(() => selected.value.size)
  const hasSelection = computed(() => selected.value.size > 0)

  function isSelected(id: string): boolean {
    return selected.value.has(id)
  }

  function toggle(id: string) {
    const s = new Set(selected.value)
    if (s.has(id)) s.delete(id)
    else           s.add(id)
    selected.value = s
  }

  function selectAll(ids: string[]) {
    selected.value = new Set(ids)
  }

  function clear() {
    selected.value = new Set()
  }

  function invert(allIds: string[]) {
    const s = new Set<string>()
    for (const id of allIds) if (!selected.value.has(id)) s.add(id)
    selected.value = s
  }

  return { selected, count, hasSelection, isSelected, toggle, selectAll, clear, invert }
}
