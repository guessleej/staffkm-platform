import { http } from './index'

export interface KbFolder {
  id:           string
  workspace_id: string
  parent_id:    string | null
  name:         string
  sort_order:   number
  kb_count:     number
  created_at:   string
  updated_at:   string
}

export interface KbFolderNode extends KbFolder {
  children: KbFolderNode[]
}

export const knowledgeApi = {
  async listBases(page = 1, pageSize = 20) {
    const { data } = await http.get('/knowledge/bases', { params: { page, page_size: pageSize } })
    return data
  },
  async createBase(payload: { name: string; description?: string; is_public?: boolean; folder_id?: string | null }) {
    const { data } = await http.post('/knowledge/bases', payload)
    return data.data
  },
  async deleteBase(kbId: string) {
    await http.delete(`/knowledge/bases/${kbId}`)
  },
  async listDocuments(kbId: string) {
    const { data } = await http.get(`/knowledge/documents/${kbId}`)
    return data.data
  },
  async uploadDocument(kbId: string, file: File, onProgress?: (p: number) => void) {
    const form = new FormData()
    form.append('file', file)
    const { data } = await http.post(`/knowledge/documents/${kbId}/upload`, form, {
      onUploadProgress: (e) => {
        if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100))
      },
    })
    return data.data
  },
  async deleteDocument(docId: string) {
    await http.delete(`/knowledge/documents/${docId}`)
  },
  async getTaskStatus(taskId: string) {
    const { data } = await http.get(`/knowledge/tasks/${taskId}`)
    return data.data
  },
  async hitTest(kbId: string, query: string, topK = 10) {
    const { data } = await http.post('/knowledge/hit-test', {
      query, kb_id: kbId, top_k: topK, similarity_threshold: 0.3,
    })
    return data.data
  },

  // ── Folders (RFC-006 C-3) ────────────────────────────────────────────────
  async listFolders(): Promise<KbFolder[]> {
    const { data } = await http.get('/knowledge/folders')
    return data.data || []
  },
  async folderTree(): Promise<KbFolderNode[]> {
    const { data } = await http.get('/knowledge/folders/tree')
    return data.data || []
  },
  async createFolder(payload: { name: string; parent_id?: string | null; sort_order?: number }): Promise<KbFolder> {
    const { data } = await http.post('/knowledge/folders', payload)
    return data.data
  },
  async updateFolder(id: string, patch: Partial<{ name: string; parent_id: string | null; sort_order: number }>): Promise<KbFolder> {
    const { data } = await http.put(`/knowledge/folders/${id}`, patch)
    return data.data
  },
  async deleteFolder(id: string): Promise<void> {
    await http.delete(`/knowledge/folders/${id}`)
  },
}
