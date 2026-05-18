export interface CaseStudy {
  slug: string
  industry: string
  company: string
  headline: string
  summary: string
  challenge: string
  solution: string
  result: string
  quote: { text: string; author: string; title: string }
  metrics: { label: string; value: string }[]
}

export const cases: CaseStudy[] = [
  {
    slug: 'tech-hr-assistant',
    industry: '科技業',
    company: '某中型科技公司',
    headline: '500 員工 HR 助理：95% 自助查詢命中率',
    summary: 'HR 一天接 80+ 通查請假規則、報帳、出差規定的電話，導入 staffKM 後 95% 員工問題自助解決。',
    challenge:
      'HR 部門 4 人服務 500 員工，每天平均 80 通電話、120 封 email 詢問同樣的問題：請假天數計算、報帳流程、出差費標準、員工福利。SOP 散在 Confluence、Google Drive、紙本，員工找不到。',
    solution:
      '將 HR 政策 PDF、員工手冊、Q&A 全部匯入 staffKM 知識庫（bge-m3 中文 embedding）。建 HR 助理 application，串 Slack bot，員工問問題秒回。再用 Workflow 自動化請假表單初步審查。',
    result:
      '上線 6 週後：HR 來電 / email 量降 70%、自助查詢命中率 95%、HR 團隊釋出 1.5 個人力 FTE 投入策略性工作。',
    quote: {
      text: '從前我們花 30% 時間回答同樣的問題。現在員工自己問 AI，我們可以做真正的 HR Business Partner 工作。',
      author: '張 OO',
      title: 'HR Director',
    },
    metrics: [
      { label: 'HR 來電量下降', value: '70%' },
      { label: '自助命中率', value: '95%' },
      { label: '釋出 FTE', value: '1.5' },
      { label: '導入時間', value: '6 週' },
    ],
  },
  {
    slug: 'bank-it-helpdesk',
    industry: '金融業',
    company: '某區域銀行',
    headline: 'IT helpdesk：L1 工單量減少 60%',
    summary: '銀行 IT 部門用 staffKM 接住 L1 工單，工程師專注 L2/L3，員工平均等待時間從 4 小時縮到 2 分鐘。',
    challenge:
      'IT 部門 12 人服務 2000+ 員工，L1 工單（密碼重設、VPN 設定、印表機驅動、O365 帳號）佔 65% 工時。員工開單後平均等 4 小時。',
    solution:
      '導入 staffKM IT helpdesk application：串 AD（密碼自助重設）、串內部 wiki（VPN / 印表機 SOP）、串 Service Now（自動開單）。用 Workflow 編輯器設「先 AI 嘗試、無法解決才轉人工」分流。',
    result:
      '3 個月後：L1 工單量降 60%、員工平均等待時間從 240 分鐘降到 2 分鐘、IT 滿意度從 72 分升到 91 分。',
    quote: {
      text: '最有感的是密碼重設。以前每週 50 通電話，現在 0 通。週末值班壓力小很多。',
      author: '李 OO',
      title: 'IT Operations Manager',
    },
    metrics: [
      { label: 'L1 工單量下降', value: '60%' },
      { label: '等待時間', value: '240 → 2 min' },
      { label: 'IT 滿意度', value: '72 → 91' },
      { label: 'ROI', value: '4 個月回本' },
    ],
  },
  {
    slug: 'retail-onboarding',
    industry: '零售業',
    company: '某連鎖零售集團',
    headline: '新員工 onboarding：訓練時間從 3 週降到 5 天',
    summary: '300 間門市每月招 50+ 新人，用 staffKM 知識庫 + 對話練習，新人 5 天就能獨立站台。',
    challenge:
      '零售業流動率高，每月 50+ 新人入職。傳統 3 週課堂訓練：講師資源不夠、新人記不住、上線後還是一直問。產品 SKU 5000+、退換貨規則複雜、會員制度年改 2 次。',
    solution:
      '把產品手冊、退換貨 SOP、會員制度、收銀機操作影片全進 staffKM。新人用「對話練習模式」模擬客戶情境（AI 扮客戶提刁鑽問題），practice → feedback 循環。店長後台看訓練進度。',
    result:
      '新人 onboarding 時間從 3 週縮到 5 天、上線後第一週「問店長」次數降 80%、客訴率降 30%。',
    quote: {
      text: '以前新人前兩週幾乎不能算戰力。現在第三天就敢面對客人，第二週能 cover 假日班。',
      author: '王 OO',
      title: 'Regional Operations Lead',
    },
    metrics: [
      { label: '訓練時間', value: '3 週 → 5 天' },
      { label: '客訴率下降', value: '30%' },
      { label: '新人「問店長」次數', value: '-80%' },
      { label: '門市覆蓋', value: '300 間' },
    ],
  },
]

export function findCase(slug: string): CaseStudy | undefined {
  return cases.find((c) => c.slug === slug)
}
