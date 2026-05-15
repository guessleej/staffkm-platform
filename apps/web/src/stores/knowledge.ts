import { defineStore } from 'pinia'
import { ref } from 'vue'
import { http } from '../api/index'

export interface KnowledgeBase {
  id: string
  name: string
  description?: string
  status: string
  embedding_model: string
  is_public: boolean
  created_at: string
  updated_at: string
  doc_count?: number
  para_count?: number
}

export interface Document {
  id: string
  knowledge_base_id: string
  name: string
  file_type?: string
  file_size: number
  status: string
  paragraph_count: number
  char_count: number
  created_at: string
}

export const useKnowledgeStore = defineStore('knowledge', () => {
  const knowledgeBases = ref<KnowledgeBase[]>([])
  const currentKb = ref<KnowledgeBase | null>(null)
  const documents = ref<Document[]>([])
  const loading = ref(false)

  async function fetchKnowledgeBases() {
    loading.value = true
    try {
      const { data } = await http.get('/knowledge/bases')
      knowledgeBases.value = data.data?.items ?? data.data ?? []
      return knowledgeBases.value
    } finally {
      loading.value = false
    }
  }

  async function createKnowledgeBase(payload: { name: string; description?: string; embedding_model?: string; is_public?: boolean }) {
    const { data } = await http.post('/knowledge/bases', payload)
    knowledgeBases.value.unshift(data.data)
    return data.data
  }

  async function updateKnowledgeBase(id: string, payload: Partial<KnowledgeBase>) {
    const { data } = await http.put(`/knowledge/bases/${id}`, payload)
    const idx = knowledgeBases.value.findIndex(kb => kb.id === id)
    if (idx !== -1) knowledgeBases.value[idx] = data.data
    return data.data
  }

  async function deleteKnowledgeBase(id: string) {
    await http.delete(`/knowledge/bases/${id}`)
    knowledgeBases.value = knowledgeBases.value.filter(kb => kb.id !== id)
    if (currentKb.value?.id === id) currentKb.value = null
  }

  async function fetchDocuments(kbId: string) {
    loading.value = true
    try {
      const { data } = await http.get(`/knowledge/bases/${kbId}/documents`)
      documents.value = data.data?.items ?? data.data ?? []
      return documents.value
    } finally {
      loading.value = false
    }
  }

  async function uploadDocument(kbId: string, file: File) {
    const formData = new FormData()
    formData.append('file', file)
    const { data } = await http.post(`/knowledge/bases/${kbId}/documents`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    documents.value.unshift(data.data)
    return data.data
  }

  async function deleteDocument(kbId: string, docId: string) {
    await http.delete(`/knowledge/bases/${kbId}/documents/${docId}`)
    documents.value = documents.value.filter(d => d.id !== docId)
  }

  function selectKb(kb: KnowledgeBase) {
    currentKb.value = kb
  }

  return {
    knowledgeBases,
    currentKb,
    documents,
    loading,
    fetchKnowledgeBases,
    createKnowledgeBase,
    updateKnowledgeBase,
    deleteKnowledgeBase,
    fetchDocuments,
    uploadDocument,
    deleteDocument,
    selectKb,
  }
})
