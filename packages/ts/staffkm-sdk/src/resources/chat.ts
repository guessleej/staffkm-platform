import { AxiosInstance } from 'axios'

export interface ChatStreamHandlers {
  onToken: (token: string) => void
  onDone?: () => void
  onError?: (e: any) => void
}

export class ChatResource {
  constructor(private http: AxiosInstance) {}

  async send(applicationId: string, message: string, conversationId?: string): Promise<any> {
    const body: Record<string, any> = { user_input: message }
    if (conversationId) body.conversation_id = conversationId
    const r = await this.http.post(`/api/v1/applications/${applicationId}/chat`, body)
    return r.data
  }

  /**
   * SSE streaming chat. Uses axios responseType: 'stream' (Node).
   * In browsers, prefer the EventSource / fetch + ReadableStream variants
   * (planned for v4.6).
   */
  async stream(
    applicationId: string,
    message: string,
    handlers: ChatStreamHandlers,
    conversationId?: string,
  ): Promise<void> {
    const body: Record<string, any> = { user_input: message }
    if (conversationId) body.conversation_id = conversationId

    const response = await this.http.post(
      `/api/v1/applications/${applicationId}/chat`,
      body,
      { responseType: 'stream' },
    )

    const stream: any = response.data
    let buf = ''
    return new Promise<void>((resolve, reject) => {
      stream.on('data', (chunk: Buffer) => {
        buf += chunk.toString('utf-8')
        let idx
        while ((idx = buf.indexOf('\n')) >= 0) {
          const line = buf.slice(0, idx).trim()
          buf = buf.slice(idx + 1)
          if (!line || !line.startsWith('data:')) continue
          const data = line.slice(5).trim()
          if (data === '[DONE]') {
            handlers.onDone?.()
            resolve()
            return
          }
          try {
            const parsed = JSON.parse(data)
            const token = typeof parsed === 'object' && parsed?.token ? parsed.token : String(parsed)
            handlers.onToken(token)
          } catch {
            handlers.onToken(data)
          }
        }
      })
      stream.on('end', () => {
        handlers.onDone?.()
        resolve()
      })
      stream.on('error', (err: any) => {
        handlers.onError?.(err)
        reject(err)
      })
    })
  }
}
