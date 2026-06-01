/**
 * MaxKB v2.8：對話中動態切 model / KB（單次 override，不改 application 預設）
 *
 * - `model`   為空字串時表示用 application 預設
 * - `kb_ids`  為空陣列時表示用 conversation/application 預設 KBs
 *
 * 由 ChatLayout 提供 picker UI、ChatView 在 streamChat() 時讀取並送進後端。
 *
 * v5.12: 持久化到 localStorage（原本純記憶體 → reload 就清空，使用者選的 KB 莫名消失、
 *   還誤判「沒生效/資料不見」）。改為存盤 + 還原，並由 ChatLayout 登出時清除（避免同機換帳號殘留）。
 */
import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const CHAT_OVERRIDE_LS_KEY = 'staffkm.chat_override'

function loadInit(): { model: string; kb_ids: string[] } {
  try {
    const raw = localStorage.getItem(CHAT_OVERRIDE_LS_KEY)
    if (raw) {
      const o = JSON.parse(raw)
      return {
        model: typeof o?.model === 'string' ? o.model : '',
        kb_ids: Array.isArray(o?.kb_ids) ? o.kb_ids.filter((x: any) => typeof x === 'string') : [],
      }
    }
  } catch { /* 壞掉的 JSON 就忽略，用預設 */ }
  return { model: '', kb_ids: [] }
}

export const useChatOverrideStore = defineStore('chatOverride', () => {
  const init = loadInit()
  const model = ref<string>(init.model)
  const kb_ids = ref<string[]>(init.kb_ids)

  // 任一變更即寫盤 → reload 後還原（deep 因 kb_ids 是陣列）
  watch([model, kb_ids], () => {
    try {
      localStorage.setItem(CHAT_OVERRIDE_LS_KEY, JSON.stringify({ model: model.value, kb_ids: kb_ids.value }))
    } catch { /* localStorage 滿/被擋 → 不致命 */ }
  }, { deep: true })

  function reset() {
    model.value = ''
    kb_ids.value = []
    try { localStorage.removeItem(CHAT_OVERRIDE_LS_KEY) } catch { /* ignore */ }
  }

  return { model, kb_ids, reset }
})
