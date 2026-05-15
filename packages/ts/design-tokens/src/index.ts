/**
 * @staffkm/design-tokens — TypeScript runtime exports
 *
 * 提供型別安全的 token 名稱常數；CSS 值仍從 CSS variable 拿。
 */

export const colors = {
  brand:   { 50: 'brand-50', 100: 'brand-100', 200: 'brand-200', 300: 'brand-300', 400: 'brand-400', 500: 'brand-500', 600: 'brand-600', 700: 'brand-700', 800: 'brand-800', 900: 'brand-900', 950: 'brand-950' },
  neutral: { 50: 'neutral-50', 100: 'neutral-100', 200: 'neutral-200', 300: 'neutral-300', 400: 'neutral-400', 500: 'neutral-500', 600: 'neutral-600', 700: 'neutral-700', 800: 'neutral-800', 900: 'neutral-900', 950: 'neutral-950' },
  success: { 50: 'success-50', 500: 'success-500', 600: 'success-600', 700: 'success-700' },
  warning: { 50: 'warning-50', 500: 'warning-500', 600: 'warning-600', 700: 'warning-700' },
  danger:  { 50: 'danger-50',  500: 'danger-500',  600: 'danger-600',  700: 'danger-700'  },
  info:    { 50: 'info-50',    500: 'info-500',    600: 'info-600',    700: 'info-700'    },
} as const

export const radius = ['none', 'sm', 'md', 'lg', 'xl', '2xl', 'full'] as const
export type Radius = typeof radius[number]

export const shadows = ['xs', 'sm', 'md', 'lg', 'xl', '2xl', 'inner', 'focus'] as const
export type Shadow = typeof shadows[number]

export const sizes = ['xs', 'sm', 'md', 'lg', 'xl'] as const
export type Size = typeof sizes[number]

export const intents = ['neutral', 'brand', 'success', 'warning', 'danger', 'info'] as const
export type Intent = typeof intents[number]

/** Helper：以 token 名取 CSS hsl() 字串。 */
export function token(role: string): string {
  return `hsl(var(--color-${role}))`
}

/** Helper：取 token 並指定透明度。 */
export function tokenAlpha(role: string, alpha: number): string {
  return `hsl(var(--color-${role}) / ${alpha})`
}
