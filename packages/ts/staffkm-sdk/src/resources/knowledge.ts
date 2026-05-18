import { AxiosInstance } from 'axios'

class KBs {
  constructor(private http: AxiosInstance) {}
  async list(): Promise<any[]> {
    const r = await this.http.get('/api/v1/knowledge')
    return r.data?.data ?? []
  }
  async create(name: string, description?: string): Promise<any> {
    const r = await this.http.post('/api/v1/knowledge', { name, description: description ?? '' })
    return r.data?.data ?? r.data
  }
}

class Docs {
  constructor(private http: AxiosInstance) {}
  /**
   * Upload a document. ``file`` may be a Buffer (Node) or Blob (browser).
   */
  async upload(kbId: string, file: any, filename: string): Promise<any> {
    // FormData differs between Node and browser; let caller pass a ready one or use this helper.
    const FD: any = (globalThis as any).FormData
    if (!FD) throw new Error('FormData not available in this runtime; build a multipart body manually')
    const fd = new FD()
    fd.append('file', file, filename)
    const r = await this.http.post(`/api/v1/knowledge/${kbId}/documents`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return r.data?.data ?? r.data
  }
}

export class KnowledgeResource {
  kbs: KBs
  docs: Docs
  constructor(private http: AxiosInstance) {
    this.kbs = new KBs(http)
    this.docs = new Docs(http)
  }

  async hitTest(kbId: string, query: string, topK = 5): Promise<any[]> {
    const r = await this.http.post(`/api/v1/knowledge/${kbId}/hit_test`, { query, top_k: topK })
    return r.data?.data ?? []
  }
}
