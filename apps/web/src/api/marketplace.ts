/**
 * Public workflow marketplace API client — v4.10 J.
 * 後端：services/agent/app/api/marketplace.py（gateway PUBLIC_PREFIXES `/api/v1/public/`）
 *
 * READ endpoints 不需 JWT；rate 需登入（http interceptor 已自動帶 token）。
 */
import { http } from './index'

export interface MarketplaceTemplate {
  id:                 string
  name:               string
  description:        string
  category:           string | null
  tags:               string[]
  cover_image_url:    string | null
  publisher_name:     string | null
  publisher_url:      string | null
  license:            string | null
  install_count:      number
  verified:           boolean
  rating_avg:         number | null
  rating_count:       number
  created_at:         string
}

export interface MarketplaceTemplateDetail extends MarketplaceTemplate {
  schema_json:        Record<string, any>
  updated_at:         string
  recent_ratings:     {
    user_id:    string
    rating:     number
    comment:    string | null
    created_at: string
  }[]
}

export interface ListResult {
  items:      MarketplaceTemplate[]
  page:       number
  page_size:  number
  total:      number
}

export interface CategoryItem {
  category: string
  count:    number
}

export type SortOption = 'popular' | 'recent' | 'rating'

export interface ListParams {
  category?:  string
  tag?:       string
  search?:    string
  sort?:      SortOption
  page?:      number
  page_size?: number
}

const BASE = '/public/marketplace'

export const marketplaceApi = {
  async list(params: ListParams = {}): Promise<ListResult> {
    const { data } = await http.get(BASE, { params })
    return data.data
  },

  async categories(): Promise<CategoryItem[]> {
    const { data } = await http.get(`${BASE}/categories`)
    return data.data.items
  },

  async detail(id: string): Promise<MarketplaceTemplateDetail> {
    const { data } = await http.get(`${BASE}/${id}`)
    return data.data
  },

  async rate(id: string, rating: number, comment?: string): Promise<void> {
    await http.post(`${BASE}/${id}/rate`, { rating, comment: comment || null })
  },
}
