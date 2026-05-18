import { http } from './index'

export interface SystemSetting {
  key: string
  value: any
  description: string | null
  updated_at: string
  updated_by?: string | null
}

export const systemSettingsApi = {
  async list(): Promise<{ items: SystemSetting[] }> {
    const r = await http.get('/admin/system-settings')
    return r.data?.data
  },
  update: (key: string, value: any) =>
    http.put(`/admin/system-settings/${encodeURIComponent(key)}`, { value }),
}
