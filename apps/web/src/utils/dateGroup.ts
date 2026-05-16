/**
 * 把含 updated_at / created_at 的清單依「相對日期」分群：
 *   今天 / 昨天 / 過去 7 天 / 過去 30 天 / 更早
 *
 * 用在 ConversationHistoryDrawer 等需要時間分群的清單。
 */
export type DateGroupKey = 'today' | 'yesterday' | 'last7' | 'last30' | 'older'

export interface DateGroup<T> {
  key: DateGroupKey
  label: string
  items: T[]
}

const LABELS: Record<DateGroupKey, string> = {
  today:     '今天',
  yesterday: '昨天',
  last7:     '過去 7 天',
  last30:    '過去 30 天',
  older:     '更早',
}

function startOfDay(d: Date): number {
  const x = new Date(d)
  x.setHours(0, 0, 0, 0)
  return x.getTime()
}

export function classifyDate(iso: string, now: Date = new Date()): DateGroupKey {
  const t = new Date(iso).getTime()
  const today = startOfDay(now)
  const oneDay = 86_400_000
  if (t >= today) return 'today'
  if (t >= today - oneDay) return 'yesterday'
  if (t >= today - 7 * oneDay) return 'last7'
  if (t >= today - 30 * oneDay) return 'last30'
  return 'older'
}

export function groupByDate<T>(
  items: T[],
  pickDate: (it: T) => string,
  now: Date = new Date(),
): DateGroup<T>[] {
  const order: DateGroupKey[] = ['today', 'yesterday', 'last7', 'last30', 'older']
  const buckets: Record<DateGroupKey, T[]> = {
    today: [], yesterday: [], last7: [], last30: [], older: [],
  }
  for (const it of items) {
    const key = classifyDate(pickDate(it), now)
    buckets[key].push(it)
  }
  return order
    .filter((k) => buckets[k].length > 0)
    .map((k) => ({ key: k, label: LABELS[k], items: buckets[k] }))
}
