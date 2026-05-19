/**
 * 简体中文（zh-CN）— 默认语系。
 *
 * 命名規則：domain.subdomain.key
 *   common.*    通用 button / label
 *   nav.*       导航列
 *   chat.*      对话页面
 *   knowledge.* 知识庫
 *   app.*       应用程式
 *   batch.*     批量选擇 toolbar
 *   folder.*    数据夹树
 *   tool.*      Tool 模組
 *   skill.*     Skill 模組
 *   datasource.*数据來源
 *   admin.*     管理介面
 *   usage.*     Token 用量儀表板
 *   trigger.*   Event Triggers（M4）
 *   memory.*    Long-term Memory（M4）
 *   mcp.*       MCP Hub（M4）
 *   provider.*  Model / Media Provider
 */
export default {
  common: {
    create:    '创建',
    edit:      '编辑',
    delete:    '删除',
    cancel:    '取消',
    confirm:   '确认',
    save:      '保存',
    search:    '搜索',
    loading:   '加载中…',
    noData:    '尚無数据',
    rename:    '重新命名',
    move:      '移動',
    duplicate: '複製',
    settings:  '设置',
    logout:    '登出',
    enable:    '啟用',
    disable:   '停用',
    enabled:   '啟用',
    disabled:  '停用',
    name:      '名称',
    description:'说明',
    actions:   '操作',
    refresh:   '重新整理',
    back:      '返回',
    close:     '關閉',
    add:       '新增',
    remove:    '移除',
    yes:       '是',
    no:        '否',
    success:   '成功',
    failed:    '失败',
    required:  '必填',
  },

  nav: {
    chat:        '对话',
    apps:        '应用',
    knowledge:   '知识庫',
    agents:      '代理人',
    users:       '使用者',
    models:      '模型',
    settings:    '设置',
    advanced:    '高级',
    tools:       '工具',
    skills:      '技能',
    datasources: '数据來源',
    dataSources: '数据來源',
    usage:       'Token 用量',
    triggers:    '排程触发',
    memory:      '長期记忆',
    mcp:         'MCP Hub',
    toolsMenu:   '工具',
    adminMenu:   '管理',
  },

  chat: {
    title:           '对话',
    newChat:         '新对话',
    welcome:         '有什么可以協助你的？',
    welcomeHint:     '输入問題開始对话，或从左側选擇历史对话',
    inputPlaceholder:'输入消息給 staffKM',
    continuePlaceholder: '繼續对话…',
    historyEmpty:    '尚無对话记錄',
    groupToday:      '今天',
    groupYesterday:  '昨天',
    groupLast7:      '過去 7 天',
    groupLast30:     '過去 30 天',
    groupOlder:      '更早',
  },

  knowledge: {
    title:       '知识庫',
    createKb:    '创建知识庫',
    docCount:    '{n} 个文件',
    charCount:   '{n} 字符',
  },

  app: {
    title:       'AI 应用',
    createApp:   '新增应用',
    typeSimple:  '简易問答',
    typeWorkflow:'工作流',
  },

  tool: {
    title:        '工具',
    create:       '创建工具',
    countLabel:   '共 {n} 个',
    emptyHint:    '尚未创建工具。Tool 可以是 HTTP API、MCP 连接、shell 指令等。',
    kindHttp:     'HTTP API',
    kindMcp:      'MCP',
    kindShell:    'Shell 指令',
    kindCustom:   '自訂',
    tryRun:       '試跑',
    deleteConfirm:'確定要删除此工具？',
  },

  skill: {
    title:        'Skills（可重用 prompt 技能）',
    create:       '创建 Skill',
    emptyHint:    '尚未创建 Skill。Skill 是可重用的 prompt 范本，可在多个 Application 中呼叫。',
    promptTpl:    'Prompt template',
    deleteConfirm:'確定要删除此 Skill？',
  },

  datasource: {
    title:        '数据來源',
    create:       '创建数据來源',
    testConn:     '測試连接',
    syncNow:      '立即同步',
    lastSynced:   '上次同步：{at}',
    kindPostgres: 'PostgreSQL',
    kindMysql:    'MySQL',
    kindApi:      'HTTP API',
  },

  batch: {
    select:       '批量选擇',
    selectedCount:'已选 {n} 項',
    moveTo:       '移至…',
    selectAll:    '全选',
    clear:        '取消选取',
  },

  folder: {
    root:         '根目錄',
    addFolder:    '新增数据夹',
    rename:       '重新命名',
  },

  workspace: {
    placeholder:  '未选擇工作區',
    owner:        '擁有者',
    admin:        '管理员',
    editor:       '编辑者',
    viewer:       '检视者',
  },

  theme: {
    light:        '切換到淺色模式',
    dark:         '切換到深色模式',
  },

  // ── M3 ─────────────────────────────────────────────────────────
  admin: {
    usersTitle:    '使用者管理',
    modelsTitle:   '模型供应商管理',
    systemTitle:   '系統设置',
    usageTitle:    'Token 用量 / Quota',
  },

  usage: {
    monthLabel:        '本月（{m}）',
    tokensTotal:       '總 token',
    costUsd:           '本月成本（USD）',
    requests:          '请求数',
    usedOf:            '已用 / 上限',
    noQuota:           '未设置上限（無限制）',
    quotaSection:      'Quota 设置',
    quotaHint:         '留空表示無上限；超過上限時新请求回 429。',
    monthlyTokenCap:   '月 token 上限',
    monthlyCostCap:    '月成本上限（USD）',
    notLimited:        '不限',
    saveQuota:         '保存 Quota',
    recentTitle:       '最近用量（最多 50 筆）',
    empty:             '尚無用量记录',
    refreshed:         '已重新整理',
  },

  provider: {
    typeLabel:         '類型',
    baseUrl:           'Base URL（选填）',
    apiKey:            'API Key',
    localNoKey:        '此供应商为地端服務，無需 API Key',
    defaultBase:       '默认：{url}',
    modelId:           '模型 ID',
    modelDisplayName:  '顯示名称（选填）',
    modelType:         '模型類型',
    isDefault:         '設为此類型的默认模型',
    recommended:       '建議：{list}',
  },

  // ── M4 ─────────────────────────────────────────────────────────
  trigger: {
    title:           '排程触发',
    create:          '创建 Trigger',
    kind:            '類型',
    kindInterval:    '固定間隔',
    kindCron:        'Cron',
    kindWebhook:     'Webhook',
    intervalSec:     '間隔秒数',
    cronExpr:        'Cron 表達式',
    nextFire:        '下次触发',
    lastFire:        '上次触发',
    runsTitle:       '触发历史',
    statusQueued:    '待執行',
    statusRunning:   '執行中',
    statusOk:        '成功',
    statusError:     '失败',
  },

  memory: {
    title:           '長期记忆',
    create:          '新增记忆',
    content:         '內容',
    scope:           '范圍',
    scopeUser:       '个人',
    scopeApp:        '应用',
    scopeTeam:       '團隊',
    importance:      '重要度',
    tags:            '標籤',
    searchPlaceholder:'搜索记忆…',
    empty:           '尚無记忆；对话內容可手動加入或由 workflow 自動寫入。',
  },

  mcp: {
    title:           'MCP Hub',
    createServer:    '新增 MCP Server',
    transport:       '傳输協定',
    url:             '端點 URL',
    refresh:         '重抓 tools',
    cachedTools:     '已快取的 Tools',
    lastRefreshed:   '上次重抓：{at}',
    callTool:        '呼叫 Tool',
    empty:           '尚未注冊任何 MCP Server。',
  },
}
