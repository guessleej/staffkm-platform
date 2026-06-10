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
  async listBases(page = 1, pageSize = 500) {   // v5.12: 提高預設避免 >20 KB 靜默截斷（無分頁 UI）
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
  // v5.13 LLM Wiki
  async generateWiki(kbId: string) {
    const { data } = await http.post(`/knowledge/bases/${kbId}/wiki/generate`)
    return data.data
  },
  async getWiki(kbId: string) {
    const { data } = await http.get(`/knowledge/bases/${kbId}/wiki`)
    return data.data as { status: any; pages: Array<{ id: string; title: string; document_id: string | null; is_index: boolean }> }
  },
  async getWikiPage(kbId: string, pageId: string) {
    const { data } = await http.get(`/knowledge/bases/${kbId}/wiki/pages/${pageId}`)
    return data.data as { id: string; title: string; content: string; is_index: boolean }
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

  // — KB 資源授權 + 關聯資源（Round 10-4）
  async listKbGrants(kbId: string) {
    const { data } = await http.get(`/knowledge/bases/${kbId}/grants`)
    return data.data || []
  },
  async addKbGrant(kbId: string, body: {
    principal_type: 'user' | 'role' | 'workspace';
    principal_id: string;
    access?: 'read' | 'edit' | 'manage';
  }) {
    const { data } = await http.post(`/knowledge/bases/${kbId}/grants`, body)
    return data.data
  },
  async deleteKbGrant(kbId: string, grantId: string) {
    await http.delete(`/knowledge/bases/${kbId}/grants/${grantId}`)
  },
  async kbRelatedResources(kbId: string): Promise<{ applications: { id: string; name: string; type: string; status: string; updated_at: string }[] }> {
    const { data } = await http.get(`/knowledge/bases/${kbId}/related-resources`)
    return data.data || { applications: [] }
  },

  // — Workflow KB（Round 10-5 / RFC-013）
  async convertToWorkflowKB(kbId: string, source_workflow_id: string) {
    const { data } = await http.post(`/knowledge/bases/${kbId}/convert-to-workflow`, { source_workflow_id })
    return data.data
  },
  async getKbSourceInfo(kbId: string) {
    const { data } = await http.get(`/knowledge/bases/${kbId}/source-info`)
    return data.data
  },

  // — Sprint 16：Web KB 同步
  async syncFromWeb(kbId: string, url: string): Promise<{ task_id?: string | null }> {
    const { data } = await http.post(`/knowledge/bases/${kbId}/web-sync`, { url })
    return data.data || {}
  },
  // — Sprint 18-C：批次多 URL 同步（最多 20）
  async syncFromWebBatch(kbId: string, urls: string[]): Promise<{ url_count: number; task_ids: string[] }> {
    const { data } = await http.post(`/knowledge/bases/${kbId}/web-sync/batch`, { urls })
    return data.data || { url_count: 0, task_ids: [] }
  },
  // — Sprint 19.x：從 sitemap.xml 抓 URL 清單 + 批次同步
  async syncFromSitemap(kbId: string, body: { sitemap_url: string; max_urls?: number; url_filter?: string }):
    Promise<{ url_count: number; task_ids: string[]; sample: string[] }> {
    const { data } = await http.post(`/knowledge/bases/${kbId}/web-sync/sitemap`, body)
    return data.data || { url_count: 0, task_ids: [], sample: [] }
  },
  async getKbSyncInfo(kbId: string): Promise<{
    source_type: 'manual' | 'workflow' | 'web';
    source_url: string | null;
    sync_status: 'pending' | 'running' | 'ready' | 'failed' | null;
    sync_error: string | null;
    last_synced_at: string | null;
  }> {
    const { data } = await http.get(`/knowledge/bases/${kbId}/sync-info`)
    return data.data
  },

  // — 段落排序（v2.1 11-3）
  async reorderParagraphs(docId: string, orderedIds: string[]) {
    const { data } = await http.put(`/knowledge/paragraphs/doc/${docId}/reorder`, { ordered_ids: orderedIds })
    return data.data
  },
  async moveParagraph(paragraphId: string, direction: 'up' | 'down' | 'top' | 'bottom') {
    const { data } = await http.post(`/knowledge/paragraphs/${paragraphId}/move?direction=${direction}`)
    return data.data
  },

  // — v5.x：MaxKB parity 段落編輯
  async addParagraph(docId: string, body: { content: string; title?: string; order_index?: number }) {
    const { data } = await http.post(`/knowledge/paragraphs/doc/${docId}/add`, body)
    return data.data
  },
  async toggleParagraph(paragraphId: string) {
    const { data } = await http.patch(`/knowledge/paragraphs/${paragraphId}/toggle`)
    return data.data
  },
  async updateParagraph(paragraphId: string, body: { content?: string; title?: string; is_active?: boolean }) {
    const { data } = await http.patch(`/knowledge/paragraphs/${paragraphId}`, body)
    return data.data
  },
  async splitParagraph(paragraphId: string, body: { separator?: string; positions?: number[] }) {
    const { data } = await http.post(`/knowledge/paragraphs/${paragraphId}/split`, body)
    return data.data
  },
  async mergeParagraphs(paragraphIds: string[]) {
    const { data } = await http.post(`/knowledge/paragraphs/merge`, { paragraph_ids: paragraphIds })
    return data.data
  },
  async bulkParagraphAction(action: 'delete' | 'enable' | 'disable' | 'regen_embedding', paragraphIds: string[]) {
    const { data } = await http.post(`/knowledge/paragraphs/bulk`, { action, paragraph_ids: paragraphIds })
    return data.data
  },
  async hitTestParagraph(paragraphId: string, query: string) {
    const { data } = await http.post(`/knowledge/paragraphs/${paragraphId}/hit-test`, { query })
    return data.data
  },
  async deleteParagraph(paragraphId: string) {
    await http.delete(`/knowledge/paragraphs/${paragraphId}`)
  },

  // — v2.8 H1：整 KB metadata 匯出 / 匯入
  async exportKb(kbId: string, includeEmbeddings = false): Promise<Blob> {
    const r = await http.get(`/knowledge/bases/${kbId}/export`, {
      params: { include_embeddings: includeEmbeddings ? 1 : 0 },
      responseType: 'blob',
    })
    return r.data as Blob
  },
  async importKb(file: File, renameTo?: string): Promise<{ kb_id: string; documents: number; paragraphs: number }> {
    const form = new FormData()
    form.append('file', file)
    const params: Record<string, any> = {}
    if (renameTo) params.rename_to = renameTo
    const { data } = await http.post('/knowledge/bases/import', form, { params })
    return data.data
  },

  // — Workflow KB inline-write（v2.1 11-1，給 SDK / 工具用）
  async inlineWrite(kbId: string, body: {
    content: string;
    title?: string;
    source?: string;
    chunking?: 'single' | 'auto' | 'paragraph';
    upsert_key?: string;
  }) {
    const { data } = await http.post(`/knowledge/documents/${kbId}/inline-write`, body)
    return data.data
  },

  // — GraphRAG 知識圖譜（v5.11.x）：啟用/重建、停用、總覽（實體/關係/社群）
  async rebuildGraph(kbId: string) {
    const { data } = await http.post(`/knowledge/bases/${kbId}/graph/rebuild`)
    return data.data
  },
  async disableGraph(kbId: string) {
    const { data } = await http.post(`/knowledge/bases/${kbId}/graph/disable`)
    return data.data
  },
  async getGraphOverview(kbId: string): Promise<{
    graph_enabled: boolean; entities: number; relations: number; total: number
    communities: { id: string; title: string; summary: string; size: number; cohesion_score: number; entities: string[] }[]
  }> {
    const { data } = await http.get(`/knowledge/bases/${kbId}/graph/communities`)
    return data.data
  },

  // — Embedding 熱換（v5.11.x）：觸發全庫重嵌 + 查進度（系統級）
  async reindexEmbedding(modelName: string) {
    const { data } = await http.post(`/knowledge/embedding/reindex`, { model_name: modelName })
    return data.data
  },
  async getReindexStatus(): Promise<{
    progress: { status: string; done?: number; total?: number; model?: string; target_dim?: number; migrated?: boolean; error?: string }
    active: { model: string; dim: number } | null
  }> {
    const { data } = await http.get(`/knowledge/embedding/reindex`)
    return data.data
  },
}
