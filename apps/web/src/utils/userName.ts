/** v2.8：使用者全名顯示統一 helper
 *
 * 規則：display_name 優先；fallback username；都沒有 → '—'
 * 為避免每個 view 自己寫 `u.display_name || u.username`，集中於此。
 */
export interface UserNameLike {
  display_name?: string | null
  displayName?: string | null
  username?: string | null
  name?: string | null
  email?: string | null
}

export function formatUserName(user: UserNameLike | null | undefined): string {
  if (!user) return '—'
  const dn = (user.display_name ?? user.displayName ?? '').toString().trim()
  if (dn) return dn
  const un = (user.username ?? user.name ?? '').toString().trim()
  if (un) return un
  const em = (user.email ?? '').toString().trim()
  return em || '—'
}
