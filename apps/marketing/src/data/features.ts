export interface Feature {
  icon: string
  title: string
  description: string
}

export const features: Feature[] = [
  {
    icon: '📚',
    title: '知識庫管理 (RAG)',
    description: '上傳 PDF / Word / 網頁，自動 chunk + embedding。bge-m3 中文檢索精準度高，命中率即時可看。',
  },
  {
    icon: '🧩',
    title: 'Workflow 編輯器',
    description: '30+ 節點拖拉組合：LLM / RAG / 條件 / 並行 / Sandbox / Webhook，行政流程自動化。',
  },
  {
    icon: '🔌',
    title: '多模型切換',
    description: 'OpenAI / Anthropic / Gemini / Ollama / Bedrock — 25+ provider 抽象介面，換 model 不改 application。',
  },
  {
    icon: '🏢',
    title: '多租戶 / 配額管理',
    description: 'Workspace 隔離、4 階 RBAC、月度 token / 成本上限。一個 instance 服務多部門。',
  },
  {
    icon: '📈',
    title: 'Audit log / Observability',
    description: '完整 audit trail、OTel + Prometheus + Grafana + Jaeger，6 條 alert、明文 SLO。',
  },
  {
    icon: '🔐',
    title: 'On-prem 部署',
    description: 'Helm chart 一鍵起 K8s；Docker Compose 5 分鐘地端 demo。資料不出園區。',
  },
]
