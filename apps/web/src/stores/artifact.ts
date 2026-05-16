/**
 * Artifact store — 全域右側 slide-in 預覽欄狀態。
 *
 * 任何元件（chat citation、workflow node、document card …）都可
 * 呼叫 open(artifact) 觸發 ArtifactPane 顯示。
 *
 * 支援的 artifact kind（discriminated union）：
 *   - 'document' — 純文字 / markdown 文件
 *   - 'code'     — 程式碼片段（含 language）
 *   - 'image'    — 圖片 URL
 *   - 'workflow' — workflow 視覺化（傳 nodes/edges）
 *   - 'iframe'   — 任意 URL 內嵌
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export type Artifact =
  | { kind: 'document'; title: string; content: string; mime?: string }
  | { kind: 'code';     title: string; content: string; language?: string }
  | { kind: 'image';    title: string; src: string;     alt?: string }
  | { kind: 'workflow'; title: string; nodes: any[];    edges: any[] }
  | { kind: 'iframe';   title: string; src: string }

export const useArtifactStore = defineStore('artifact', () => {
  const current = ref<Artifact | null>(null)

  const isOpen = computed(() => current.value !== null)

  function open(a: Artifact) {
    current.value = a
  }

  function close() {
    current.value = null
  }

  return { current, isOpen, open, close }
})
