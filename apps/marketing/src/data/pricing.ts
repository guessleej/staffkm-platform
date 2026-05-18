export interface PricingPlan {
  id: string
  name: string
  price: string
  priceNote: string
  cta: string
  ctaHref: string
  highlight?: boolean
  badge?: string
  features: string[]
}

export const plans: PricingPlan[] = [
  {
    id: 'trial',
    name: 'Free Trial',
    price: 'NT$ 0',
    priceNote: '14 天試用',
    cta: '免費試用',
    ctaHref: '/signup',
    features: [
      '100K tokens / 月',
      '1 user',
      '1 workspace',
      '社群支援',
      '基本 RAG 知識庫',
    ],
  },
  {
    id: 'starter',
    name: 'Starter',
    price: '$29',
    priceNote: '/ 月',
    cta: '開始使用',
    ctaHref: '/signup?plan=starter',
    features: [
      '1M tokens / 月',
      '5 users',
      '3 workspaces',
      'Email 支援',
      'RAG + Workflow',
      '社群模板庫',
    ],
  },
  {
    id: 'pro',
    name: 'Pro',
    price: '$199',
    priceNote: '/ 月',
    cta: '開始使用',
    ctaHref: '/signup?plan=pro',
    highlight: true,
    badge: '最受歡迎',
    features: [
      '20M tokens / 月',
      'Unlimited users',
      '10 workspaces',
      'Slack / 優先 email 支援',
      '完整 Workflow + MCP',
      'Audit log 90 天保留',
      'SSO (OIDC)',
    ],
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 'Contact us',
    priceNote: '客製報價',
    cta: '聯絡業務',
    ctaHref: 'mailto:sales@staffkm.dev',
    features: [
      'Unlimited tokens',
      'On-prem 部署（Helm）',
      'SLA 99.9%',
      '專屬 CSM',
      '客製化整合',
      '優先 RFE',
      '安全稽核報告',
    ],
  },
]

export interface ComparisonRow {
  feature: string
  trial: string | boolean
  starter: string | boolean
  pro: string | boolean
  enterprise: string | boolean
}

export const comparison: ComparisonRow[] = [
  { feature: '月度 token', trial: '100K', starter: '1M', pro: '20M', enterprise: 'Unlimited' },
  { feature: '使用者數', trial: '1', starter: '5', pro: 'Unlimited', enterprise: 'Unlimited' },
  { feature: 'Workspace', trial: '1', starter: '3', pro: '10', enterprise: 'Unlimited' },
  { feature: 'RAG 知識庫', trial: true, starter: true, pro: true, enterprise: true },
  { feature: 'Workflow 編輯器', trial: false, starter: true, pro: true, enterprise: true },
  { feature: 'MCP / 工具', trial: false, starter: false, pro: true, enterprise: true },
  { feature: 'SSO (OIDC)', trial: false, starter: false, pro: true, enterprise: true },
  { feature: 'On-prem 部署', trial: false, starter: false, pro: false, enterprise: true },
  { feature: 'SLA', trial: false, starter: false, pro: false, enterprise: '99.9%' },
]

export interface Faq {
  q: string
  a: string
}

export const faqs: Faq[] = [
  {
    q: '可以中途升級或降級嗎？',
    a: '可以。隨時可在後台升級 / 降級，差額按比例計算（pro-rated）。',
  },
  {
    q: '超過 token 上限會發生什麼？',
    a: '超額後新請求會回 HTTP 429。Pro / Enterprise 可開啟「超額付費」（overage billing）自動續用。',
  },
  {
    q: '可以自己 host 嗎？',
    a: 'Enterprise plan 提供 Helm chart 與 Docker Compose 完整 on-prem 部署，含 backup / DR runbook。',
  },
  {
    q: '支援哪些 LLM？',
    a: 'OpenAI、Anthropic、Google Gemini、AWS Bedrock、Cohere、DeepSeek、地端 Ollama 等 25+ provider。',
  },
  {
    q: '資料安全與隱私？',
    a: 'API key Fernet 加密、Sandbox + rlimit 隔離、完整 audit log。Enterprise 提供 SOC2 / ISO27001 整合協助。',
  },
]
