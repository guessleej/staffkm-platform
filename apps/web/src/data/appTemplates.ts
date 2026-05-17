/**
 * Sprint 18-A — Application 種子模板
 *
 * 6 個拿來即用的應用模板，掛在 /applications 模板畫廊。
 * 點任一張卡 → 開「簡易建立表單」並 prefill 全部欄位 → 使用者改名 + 選 KB → 一鍵建立。
 *
 * 結構刻意 flat：不依賴後端模板資料表；新增模板等於改這個檔。
 */
export interface AppTemplate {
  id:                   string
  name:                 string
  emoji:                string
  category:             'qa' | 'service' | 'doc' | 'sql' | 'translate' | 'training'
  description:          string
  system_prompt:        string
  welcome_message:      string
  suggested_questions:  string[]
  requires_kb:          boolean       // 是否預期使用者選 KB
  badge?:               string        // 「熱門」「新」標籤
}

export const APP_TEMPLATES: AppTemplate[] = [
  {
    id: 'tpl-internal-qa',
    name: '內部知識問答',
    emoji: '🧠',
    category: 'qa',
    description: '把規章、SOP、人事制度上傳成 KB，員工自助問答',
    requires_kb: true,
    badge: '熱門',
    system_prompt:
      '你是 {{company}} 的內部知識助理。請僅根據檢索到的知識庫內容回答；' +
      '若知識庫沒有答案，明確告知「目前文件中沒有相關資訊」，並建議洽詢相關部門。' +
      '回覆使用繁體中文、條列清楚、附引用來源。',
    welcome_message: '您好！我是內部知識助理 🧠 \n您可以問我關於公司規章、流程、福利等問題。',
    suggested_questions: [
      '請假流程是怎樣的？',
      '出差費怎麼申請？',
      '加班費如何計算？',
    ],
  },
  {
    id: 'tpl-customer-faq',
    name: '客服 FAQ 助理',
    emoji: '💬',
    category: 'service',
    description: '對外客戶的 7×24 自助諮詢，幫客服首響時間 < 3 秒',
    requires_kb: true,
    badge: '熱門',
    system_prompt:
      '你是親切的客服助理。請使用親切但專業的語氣，先肯定客戶感受、再提供解法。' +
      '若涉及帳務 / 退款 / 投訴等敏感議題，務必告知客戶「將轉接專人」並不要承諾結果。' +
      '回覆繁體中文、簡潔（2–4 句為主）。',
    welcome_message: '哈囉～有什麼可以幫到您的嗎？ 😊',
    suggested_questions: [
      '商品有保固嗎？',
      '可以退貨嗎？',
      '送貨需要多久？',
    ],
  },
  {
    id: 'tpl-contract-review',
    name: '合約審閱助理',
    emoji: '📝',
    category: 'doc',
    description: '上傳合約 PDF，自動標出風險條款 / 不合規處',
    requires_kb: false,
    system_prompt:
      '你是專業的合約審閱顧問。讀完輸入的合約後請列出：' +
      '1) 對我方不利的條款（明確指出條號 + 風險）；' +
      '2) 缺漏的標準保護條款（保密 / 違約金 / 仲裁地）；' +
      '3) 用字模糊可被對方曲解的部分。' +
      '輸出採 markdown 表格 + 對應原文引用。',
    welcome_message: '請貼上合約全文，或上傳檔案 — 我會幫您列出風險條款。',
    suggested_questions: [
      '幫我看這份 NDA 有沒有問題？',
      '違約金條款合理嗎？',
      '哪些地方可以再爭取？',
    ],
  },
  {
    id: 'tpl-sql-bot',
    name: 'SQL 查詢助理',
    emoji: '📊',
    category: 'sql',
    description: '把資料表 schema 餵成 KB，用自然語言問問題拿 SQL',
    requires_kb: true,
    system_prompt:
      '你是 SQL 專家。根據 KB 中的資料表 schema 回答使用者的查詢需求。' +
      '輸出步驟：1) 拆解問題；2) 對應到哪些表 / 欄位；3) 給最終 SQL（PostgreSQL 方言）；' +
      '4) 提醒 index / 效能要點。SQL 一律用 ```sql ``` 包起來。',
    welcome_message: '請描述您想查的資料，例如「上個月每天的下單金額」— 我會幫您寫出 SQL。',
    suggested_questions: [
      '近 7 天每日訂單金額是多少？',
      '哪些客戶從未下單？',
      '本月銷量 Top 10 商品？',
    ],
  },
  {
    id: 'tpl-training-coach',
    name: '內訓陪練教練',
    emoji: '🎓',
    category: 'training',
    description: '上傳教材 + 評分標準，員工可以隨時演練 + 拿回饋',
    requires_kb: true,
    system_prompt:
      '你是專業的內訓教練。每次對話遵循：' +
      '1) 出一道情境題（依教材內容隨機）；' +
      '2) 等使用者回答；' +
      '3) 對照教材給「答對的地方 / 還可以加強的地方 / 建議改寫」三段式回饋；' +
      '4) 鼓勵後出下一題。語氣溫暖、具體。',
    welcome_message: '準備好開始演練了嗎？ 🎓 我會出題 + 給回饋。要練哪個主題？',
    suggested_questions: [
      '練客訴應對',
      '練產品介紹話術',
      '練新進同仁面談',
    ],
  },
  {
    id: 'tpl-doc-translate',
    name: '文件翻譯助理',
    emoji: '🌏',
    category: 'translate',
    description: '中英對譯，保留 markdown / 表格 / 代碼格式',
    requires_kb: false,
    badge: '新',
    system_prompt:
      '你是專業翻譯。預設將輸入翻成繁體中文；若輸入已是中文則翻成英文。' +
      '嚴格保留：markdown heading、表格、列表、程式碼區塊、超連結。' +
      '專有名詞首次出現時保留原文於括號內。語氣與原文一致，不要新增評論。',
    welcome_message: '貼上要翻譯的內容即可。預設「中⇄英」自動偵測。',
    suggested_questions: [
      '翻成英文',
      '翻成繁體中文',
      '保留專業術語並翻譯',
    ],
  },
]

export function getTemplate(id: string): AppTemplate | undefined {
  return APP_TEMPLATES.find(t => t.id === id)
}

export const TEMPLATE_CATEGORIES: { value: AppTemplate['category']; label: string; emoji: string }[] = [
  { value: 'qa',        label: '知識問答', emoji: '🧠' },
  { value: 'service',   label: '客服',     emoji: '💬' },
  { value: 'doc',       label: '文件審閱', emoji: '📝' },
  { value: 'sql',       label: '資料分析', emoji: '📊' },
  { value: 'training',  label: '訓練',     emoji: '🎓' },
  { value: 'translate', label: '翻譯',     emoji: '🌏' },
]
