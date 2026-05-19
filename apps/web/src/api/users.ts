import { http } from './index'

export interface User {
  id: string
  username: string
  email: string | null
  display_name: string | null
  status: string
  roles: string[]
  department: string | null
  // v2.7 X-Pack：登入方式白名單；null = 不限制
  allowed_login_methods?: string[] | null
  created_at?: string
  updated_at?: string
  last_login_at?: string
}

export interface UserListResp {
  data: User[]
  meta: { page: number; page_size: number; total: number; total_pages: number }
}

export const usersApi = {
  async list(page = 1, page_size = 20, search = ''): Promise<UserListResp> {
    const params: Record<string, any> = { page, page_size }
    if (search) params.search = search
    const r = await http.get('/admin/users', { params })
    return r.data
  },
  create: (body: { username: string; email?: string; password: string; roles?: string[]; display_name?: string }) =>
    http.post('/admin/users', body),
  setStatus: (userId: string, status: 'active' | 'inactive' | 'locked') =>
    http.patch(`/admin/users/${userId}/status`, null, { params: { status } }),
  setRole: (userId: string, roles: string[]) =>
    http.put(`/admin/users/${userId}/role`, { roles }),
  resetPassword: (userId: string, new_password: string) =>
    http.post(`/admin/users/${userId}/reset-password`, { new_password }),
  setLoginMethods: (userId: string, methods: string[] | null) =>
    http.put(`/admin/users/${userId}/login-methods`, { allowed_login_methods: methods }),
  delete: (userId: string) =>
    http.delete(`/admin/users/${userId}`),
}
