import { http } from './index'

export type BillingPlan = 'trial' | 'starter' | 'pro' | 'usage'

export interface BillingMe {
  plan: BillingPlan | string
  status: string
  credits_balance: number
  current_period_start: string | null
  current_period_end: string | null
}

export interface BillingInvoice {
  id: string
  stripe_invoice_id: string | null
  amount_usd: number
  currency: string
  status: string
  period_start: string | null
  period_end: string | null
  invoice_pdf_url: string | null
  created_at: string
}

export interface CreditLedgerEntry {
  delta_usd: number
  reason: string
  reference: string | null
  balance_after: number
  created_at: string
}

export const billingApi = {
  me: async (): Promise<BillingMe> =>
    (await http.get('/billing/me')).data.data,

  /** plan: starter | pro | usage | topup10 | topup50 | topup200 */
  checkout: async (plan: string): Promise<{ checkout_url: string }> =>
    (await http.post('/billing/checkout', { plan })).data.data,

  portal: async (): Promise<{ portal_url: string }> =>
    (await http.post('/billing/portal')).data.data,

  invoices: async (): Promise<{ items: BillingInvoice[] }> =>
    (await http.get('/billing/invoices')).data.data,

  ledger: async (): Promise<{ items: CreditLedgerEntry[] }> =>
    (await http.get('/billing/credits/ledger')).data.data,
}
