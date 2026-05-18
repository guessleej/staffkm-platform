import { http } from './index'

export type ApprovalStatus = 'pending' | 'approved' | 'rejected'

export interface WorkflowApproval {
  id: string
  run_id: string
  node_key: string
  status: ApprovalStatus
  requester: string | null
  approver_id: string | null
  approver_note: string | null
  payload: any
  created_at: string
  resolved_at: string | null
}

export const approvalApi = {
  list: async (status?: ApprovalStatus): Promise<{ items: WorkflowApproval[] }> => {
    const q = status ? `?status=${status}` : ''
    return (await http.get(`/approvals${q}`)).data.data
  },
  approve: (id: string, note?: string) =>
    http.post(`/approvals/${id}/approve`, { note }),
  reject: (id: string, note?: string) =>
    http.post(`/approvals/${id}/reject`, { note }),
}
