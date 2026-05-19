/**
 * MaxKB v2.8：對話中動態切 model / KB（單次 override，不改 application 預設）
 *
 * - `model`   為空字串時表示用 application 預設
 * - `kb_ids`  為空陣列時表示用 conversation/application 預設 KBs
 *
 * 由 ChatLayout 提供 picker UI、ChatView 在 streamChat() 時讀取並送進後端。
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useChatOverrideStore = defineStore('chatOverride', () => {
  const model = ref<string>('')
  const kb_ids = ref<string[]>([])

  function reset() {
    model.value = ''
    kb_ids.value = []
  }

  return { model, kb_ids, reset }
})
