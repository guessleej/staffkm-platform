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
  async createBase(payload: {
    name: string
    description?: string
    is_public?: boolean
    folder_id?: string | null
    chunk_strategy?: 'auto' | 'recursive' | 'markdown' | 'qa'
    chunk_size?: number
    chunk_overlap?: number
  }) {
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

  // ═════════════════════════════════════════════════════════════════════
  //  Round 10 — MaxKB parity
  // ═════════════════════════════════════════════════════════════════════
  // — 文檔操作（Round 10-1）
  async updateDocSettings(docId: string, patch: {
    name?: string; tags?: string[];
    hit_strategy?: 'rag' | 'direct' | 'both'; is_enabled?: boolean;
  }) {
    const { data } = await http.patch(`/knowledge/documents/doc/${docId}/settings`, patch)
    return data.data
  },
  async migrateDoc(docId: string, targetKbId: string) {
    const { data } = await http.post(`/knowledge/documents/doc/${docId}/migrate`, { target_kb_id: targetKbId })
    return data.data
  },
  downloadDocUrl(docId: string): string {
    const base = (import.meta as any).env?.VITE_API_BASE_URL || '/api/v1'
    return `${base}/knowledge/documents/doc/${docId}/download`
  },
  async replaceDoc(docId: string, file: File, keepChunks = false) {
    const form = new FormData()
    form.append('file', file)
    form.append('keep_chunks', String(keepChunks))
    const { data } = await http.post(`/knowledge/documents/doc/${docId}/replace`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data.data
  },
  async batchToggleDocs(kbId: string, ids: string[], enabled: boolean) {
    const { data } = await http.post(
      `/knowledge/documents/${kbId}/batch-toggle?enabled=${enabled}`,
      { document_ids: ids },
    )
    return data.data
  },
  async batchDeleteDocs(kbId: string, ids: string[]) {
    const { data } = await http.post(`/knowledge/documents/${kbId}/batch-delete`, {
      document_ids: ids,
    })
    return data.data
  },
  async listWorkspaceTags(): Promise<{ tag: string; count: number }[]> {
    const { data } = await http.get('/knowledge/documents/tags')
    return data.data || []
  },

  // — Q&A 生成（Round 10-2）
  async generateParagraphQA(paragraphId: string, opts?: { n?: number; append?: boolean; model?: string }) {
    const { data } = await http.post(`/knowledge/paragraphs/${paragraphId}/generate-qa`, opts || {})
    return data.data
  },
  async getParagraphQA(paragraphId: string) {
    const { data } = await http.get(`/knowledge/paragraphs/${paragraphId}/qa`)
    return data.data || []
  },
  async putParagraphQA(paragraphId: string, qa: { question: string; answer: string; source?: 'auto'|'manual' }[]) {
    const { data } = await http.put(`/knowledge/paragraphs/${paragraphId}/qa`, { qa })
    return data.data
  },
  async generateDocQuestions(docId: string, opts?: { per_paragraph?: number; max_paragraphs?: number; overwrite?: boolean; model?: string }) {
    const { data } = await http.post(`/knowledge/documents/doc/${docId}/generate-questions`, opts || {})
    return data.data
  },
  async getDocQuestions(docId: string): Promise<string[]> {
    const { data } = await http.get(`/knowledge/documents/doc/${docId}/questions`)
    return data.data || []
  },

  // — 匯出（Round 10-3）
  async exportExcel(kbId: string, document_ids: string[] = []): Promise<Blob> {
    const r = await http.post(`/knowledge/documents/${kbId}/export/excel`, { document_ids }, { responseType: 'blob' })
    return r.data as Blob
  },
  async exportZip(kbId: string, document_ids: string[] = []): Promise<Blob> {
    const r = await http.post(`/knowledge/documents/${kbId}/export/zip`, { document_ids }, { responseType: 'blob' })
    return r.data as Blob
  },
}
