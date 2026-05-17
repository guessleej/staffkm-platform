/**
 * Celery task control API client (knowledge service).
 * 後端：services/knowledge/app/api/tasks.py
 */
import { http } from './index'

export interface TaskStatus {
  task_id: string
  status: string
  result: unknown | null
  error: string | null
}

export const tasksApi = {
  async get(taskId: string): Promise<TaskStatus> {
    const { data } = await http.get(`/knowledge/tasks/${taskId}`)
    return data.data
  },
  // admin-only：撤回（terminate=false，只是不要再 pick up）
  async revoke(taskId: string): Promise<void> {
    await http.post(`/knowledge/tasks/${taskId}/revoke`)
  },
}
