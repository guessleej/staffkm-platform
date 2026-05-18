// v4.9 I：AI-generated workflow client
import { http } from './index'

export interface GenerateResult {
  workflow: any | null
  valid: boolean
  errors: string[]
  raw_response: string
}

export const workflowGenApi = {
  generate: async (userRequest: string, model?: string): Promise<GenerateResult> =>
    (await http.post('/workflow-gen/generate', { user_request: userRequest, model })).data.data,
}
