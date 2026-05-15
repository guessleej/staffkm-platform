import { http } from './index'

export const knowledgeApi = {
  async listBases(page = 1, pageSize = 20) {
    const { data } = await http.get('/knowledge/bases', { params: { page, page_size: pageSize } })
    return data
  },
  async createBase(payload: { name: string; description?: string; is_public?: boolean }) {
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
}
