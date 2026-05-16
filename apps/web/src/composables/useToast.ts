/**
 * useToast — 全域 toast queue（UX 對齊輪 #1）
 *
 * 用法：
 *   const toast = useToast()
 *   toast.success('已儲存')
 *   toast.error('連線失敗')
 *   toast.info('已複製')
 *   toast.warning('quota 將滿', { duration: 6000 })
 *
 * 內部以 module-level reactive ref 維護 queue；
 * 由 <ToastHost /> 元件渲染（在 App.vue 掛一份即可）。
 */
import { ref } from 'vue'

export type ToastKind = 'success' | 'error' | 'info' | 'warning'

export interface ToastItem {
  id:       number
  kind:     ToastKind
  message:  string
  duration: number
}

const _queue = ref<ToastItem[]>([])
let _nextId = 1

function _push(kind: ToastKind, message: string, opts?: { duration?: number }) {
  const id = _nextId++
  const duration = opts?.duration ?? (kind === 'error' ? 6000 : 3000)
  _queue.value.push({ id, kind, message, duration })
  if (duration > 0) {
    setTimeout(() => dismiss(id), duration)
  }
  return id
}

export function dismiss(id: number) {
  _queue.value = _queue.value.filter(t => t.id !== id)
}

export function useToast() {
  return {
    success: (msg: string, opts?: { duration?: number }) => _push('success', msg, opts),
    error:   (msg: string, opts?: { duration?: number }) => _push('error',   msg, opts),
    info:    (msg: string, opts?: { duration?: number }) => _push('info',    msg, opts),
    warning: (msg: string, opts?: { duration?: number }) => _push('warning', msg, opts),
    dismiss,
    /** 供 ToastHost 元件讀 queue */
    _queue,
  }
}
