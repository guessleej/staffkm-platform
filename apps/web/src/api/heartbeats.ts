import { http } from './index'

export interface WorkerHeartbeat {
  worker_name: string
  pid: number | null
  host: string | null
  started_at: string
  last_beat: string
  in_flight: number
  stale_seconds: number
  healthy: boolean
}

export const heartbeatsApi = {
  list: async (): Promise<{ items: WorkerHeartbeat[]; stale_threshold_sec: number }> =>
    (await http.get('/admin/heartbeats')).data.data,
}
