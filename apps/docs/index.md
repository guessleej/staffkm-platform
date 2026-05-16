---
layout: home

hero:
  name: staffKM
  text: 內部知識管理 · AI 協作平台
  tagline: 讓組織知識被找得到、用得上、留得下
  actions:
    - theme: brand
      text: 5 分鐘上手
      link: /user/getting-started
    - theme: alt
      text: 為何 staffKM
      link: /#why
    - theme: alt
      text: GitHub
      link: https://github.com/guessleej/staffkm-platform

features:
  - icon: 🏢
    title: 多租戶 + RBAC
    details: workspace + 4 階角色（owner/admin/editor/viewer）；三層隔離（Path/RBAC/SQL）
  - icon: 🤖
    title: 30+ Workflow Nodes
    details: LLM / RAG / 條件 / 並行 / 批次 / Sandbox / Webhook / Email / Schedule / Map-Reduce…
  - icon: 🔌
    title: 25+ Model Providers
    details: 地端 Ollama 預設；Anthropic / Gemini / Cohere / Bedrock / Vertex AI / DeepSeek / 智譜 / Moonshot…
  - icon: 💰
    title: Token 計帳 + Quota
    details: 月度 token / 成本上限；超額 429；管理儀表板 + per-request log
  - icon: 🔐
    title: Sandbox + KMS
    details: Workflow shell 走 subprocess + rlimit；API key Fernet 加密
  - icon: 📈
    title: 完整 Observability
    details: OTel + Prometheus + Grafana + Jaeger；6 條 alert + SLO
---

## <a id="why" /> 為何 staffKM

**目標使用者**：行政人員（找 SOP 答案）、PM（建 application 給部門用）、IT（守門、看用量、控成本）、主管（看部門知識怎麼被用）。

**對比定位**：

| 我們的選擇                       | 為什麼                                                  |
| -------------------------------- | ------------------------------------------------------- |
| 對話為中心介面（claude.ai 對標）   | 行政人員打開就會用，不需要學 dashboard                   |
| 地端 LLM 預設（Ollama）           | 資料不出園區；成本可控                                  |
| 25+ Provider 抽象                | 不被單一 vendor 鎖；可同時跑地端 + 外部備援              |
| Sandbox 嚴格隔離                  | 工作流可跑 shell 但只在 SubprocessSandbox（rlimit）內   |
| 完整 RFC + brand + UX + 文件      | 不是只把 demo 跑起來就算完                              |

> 想直接看代碼？[GitHub →](https://github.com/guessleej/staffkm-platform)
