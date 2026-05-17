/**
 * 繁體中文（zh-TW）— 預設語系。
 *
 * 命名規則：domain.subdomain.key
 *   common.*    通用 button / label
 *   nav.*       導覽列
 *   chat.*      對話畫面
 *   knowledge.* 知識庫
 *   app.*       應用程式
 *   batch.*     批量選擇 toolbar
 *   folder.*    資料夾樹
 *   tool.*      Tool 模組
 *   skill.*     Skill 模組
 *   datasource.*資料來源
 *   admin.*     管理介面
 *   usage.*     Token 用量儀表板
 *   trigger.*   Event Triggers（M4）
 *   memory.*    Long-term Memory（M4）
 *   mcp.*       MCP Hub（M4）
 *   provider.*  Model / Media Provider
 */
export default {
  common: {
    create:    '建立',
    edit:      '編輯',
    delete:    '刪除',
    cancel:    '取消',
    confirm:   '確認',
    save:      '儲存',
    search:    '搜尋',
    loading:   '載入中…',
    noData:    '尚無資料',
    rename:    '重新命名',
    move:      '移動',
    duplicate: '複製',
    settings:  '設定',
    logout:    '登出',
    enable:    '啟用',
    disable:   '停用',
    enabled:   '啟用',
    disabled:  '停用',
    name:      '名稱',
    description:'說明',
    actions:   '操作',
    refresh:   '重新整理',
    back:      '返回',
    close:     '關閉',
    add:       '新增',
    remove:    '移除',
    yes:       '是',
    no:        '否',
    success:   '成功',
    failed:    '失敗',
    required:  '必填',
  },

  nav: {
    chat:        '對話',
    apps:        '應用',
    knowledge:   '知識庫',
    agents:      '代理人',
    users:       '使用者',
    models:      '模型',
    settings:    '設定',
    advanced:    '進階',
    tools:       '工具',
    skills:      '技能',
    datasources: '資料來源',
    dataSources: '資料來源',
    usage:       'Token 用量',
    triggers:    '排程觸發',
    memory:      '長期記憶',
    mcp:         'MCP Hub',
  },

  chat: {
    title:           '對話',
    newChat:         '新對話',
    welcome:         '有什麼可以協助你的？',
    welcomeHint:     '輸入問題開始對話，或從左側選擇歷史對話',
    inputPlaceholder:'輸入訊息給 staffKM',
    continuePlaceholder: '繼續對話…',
    historyEmpty:    '尚無對話記錄',
    groupToday:      '今天',
    groupYesterday:  '昨天',
    groupLast7:      '過去 7 天',
    groupLast30:     '過去 30 天',
    groupOlder:      '更早',
  },

  knowledge: {
    title:       '知識庫',
    createKb:    '建立知識庫',
    docCount:    '{n} 個文件',
    charCount:   '{n} 字符',
  },

  app: {
    title:       'AI 應用',
    createApp:   '新增應用',
    typeSimple:  '簡易問答',
    typeWorkflow:'工作流',
  },

  tool: {
    title:        '工具',
    create:       '建立工具',
    countLabel:   '共 {n} 個',
    emptyHint:    '尚未建立工具。Tool 可以是 HTTP API、MCP 連線、shell 指令等。',
    kindHttp:     'HTTP API',
    kindMcp:      'MCP',
    kindShell:    'Shell 指令',
    kindCustom:   '自訂',
    tryRun:       '試跑',
    deleteConfirm:'確定要刪除此工具？',
  },

  skill: {
    title:        'Skills（可重用 prompt 技能）',
    create:       '建立 Skill',
    emptyHint:    '尚未建立 Skill。Skill 是可重用的 prompt 範本，可在多個 Application 中呼叫。',
    promptTpl:    'Prompt template',
    deleteConfirm:'確定要刪除此 Skill？',
  },

  datasource: {
    title:        '資料來源',
    create:       '建立資料來源',
    testConn:     '測試連線',
    syncNow:      '立即同步',
    lastSynced:   '上次同步：{at}',
    kindPostgres: 'PostgreSQL',
    kindMysql:    'MySQL',
    kindApi:      'HTTP API',
  },

  batch: {
    select:       '批量選擇',
    selectedCount:'已選 {n} 項',
    moveTo:       '移至…',
    selectAll:    '全選',
    clear:        '取消選取',
  },

  folder: {
    root:         '根目錄',
    addFolder:    '新增資料夾',
    rename:       '重新命名',
  },

  workspace: {
    placeholder:  '未選擇工作區',
    owner:        '擁有者',
    admin:        '管理員',
    editor:       '編輯者',
    viewer:       '檢視者',
  },

  theme: {
    light:        '切換到淺色模式',
    dark:         '切換到深色模式',
  },

  // ── M3 ─────────────────────────────────────────────────────────
  admin: {
    usersTitle:    '使用者管理',
    modelsTitle:   '模型供應商管理',
    systemTitle:   '系統設定',
    usageTitle:    'Token 用量 / Quota',
  },

  usage: {
    monthLabel:        '本月（{m}）',
    tokensTotal:       '總 token',
    costUsd:           '本月成本（USD）',
    requests:          '請求數',
    usedOf:            '已用 / 上限',
    noQuota:           '未設定上限（無限制）',
    quotaSection:      'Quota 設定',
    quotaHint:         '留空表示無上限；超過上限時新請求回 429。',
    monthlyTokenCap:   '月 token 上限',
    monthlyCostCap:    '月成本上限（USD）',
    notLimited:        '不限',
    saveQuota:         '儲存 Quota',
    recentTitle:       '最近用量（最多 50 筆）',
    empty:             '尚無用量紀錄',
    refreshed:         '已重新整理',
  },

  provider: {
    typeLabel:         '類型',
    baseUrl:           'Base URL（選填）',
    apiKey:            'API Key',
    localNoKey:        '此供應商為地端服務，無需 API Key',
    defaultBase:       '預設：{url}',
    modelId:           '模型 ID',
    modelDisplayName:  '顯示名稱（選填）',
    modelType:         '模型類型',
    isDefault:         '設為此類型的預設模型',
    recommended:       '建議：{list}',
  },

  // ── M4 ─────────────────────────────────────────────────────────
  trigger: {
    title:           '排程觸發',
    create:          '建立 Trigger',
    kind:            '類型',
    kindInterval:    '固定間隔',
    kindCron:        'Cron',
    kindWebhook:     'Webhook',
    intervalSec:     '間隔秒數',
    cronExpr:        'Cron 表達式',
    nextFire:        '下次觸發',
    lastFire:        '上次觸發',
    runsTitle:       '觸發歷史',
    statusQueued:    '待執行',
    statusRunning:   '執行中',
    statusOk:        '成功',
    statusError:     '失敗',
  },

  memory: {
    title:           '長期記憶',
    create:          '新增記憶',
    content:         '內容',
    scope:           '範圍',
    scopeUser:       '個人',
    scopeApp:        '應用',
    scopeTeam:       '團隊',
    importance:      '重要度',
    tags:            '標籤',
    searchPlaceholder:'搜尋記憶…',
    empty:           '尚無記憶；對話內容可手動加入或由 workflow 自動寫入。',
  },

  mcp: {
    title:           'MCP Hub',
    createServer:    '新增 MCP Server',
    transport:       '傳輸協定',
    url:             '端點 URL',
    refresh:         '重抓 tools',
    cachedTools:     '已快取的 Tools',
    lastRefreshed:   '上次重抓：{at}',
    callTool:        '呼叫 Tool',
    empty:           '尚未註冊任何 MCP Server。',
  },
}
