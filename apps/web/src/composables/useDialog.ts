/**
 * useDialog — 取代瀏覽器原生 alert / confirm（UX 對齊輪 #1）
 *
 * 用法：
 *   const dialog = useDialog()
 *   if (!(await dialog.confirm('確定要刪除？', { tone: 'danger' }))) return
 *   await dialog.alert('已完成')
 *
 * 由 <DialogHost /> 元件渲染（App.vue 掛一份）。
 * 採用 Promise 模式：confirm() 解析為 true/false；alert() 解析為 void。
 */
import { ref } from 'vue'

export type DialogTone = 'default' | 'danger' | 'success'

export interface DialogRequest {
  id:           number
  kind:         'alert' | 'confirm'
  title?:       string
  message:      string
  tone:         DialogTone
  confirmLabel: string
  cancelLabel:  string
  resolve:      (ok: boolean) => void
}

const _queue = ref<DialogRequest[]>([])
let _nextId = 1

interface CommonOpts {
  title?:        string
  tone?:         DialogTone
  confirmLabel?: string
  cancelLabel?:  string
}

function _push(kind: 'alert' | 'confirm', message: string, opts?: CommonOpts): Promise<boolean> {
  return new Promise((resolve) => {
    _queue.value.push({
      id:           _nextId++,
      kind,
      title:        opts?.title,
      message,
      tone:         opts?.tone ?? 'default',
      confirmLabel: opts?.confirmLabel ?? (kind === 'confirm' ? '確定' : '了解'),
      cancelLabel:  opts?.cancelLabel  ?? '取消',
      resolve,
    })
  })
}

export function resolveDialog(id: number, ok: boolean) {
  const idx = _queue.value.findIndex(d => d.id === id)
  if (idx === -1) return
  const req = _queue.value[idx]
  _queue.value.splice(idx, 1)
  req.resolve(ok)
}

export function useDialog() {
  return {
    alert:   (message: string, opts?: CommonOpts) => _push('alert', message, opts).then(() => undefined),
    confirm: (message: string, opts?: CommonOpts) => _push('confirm', message, opts),
    /** 供 DialogHost 元件讀 queue */
    _queue,
  }
}
