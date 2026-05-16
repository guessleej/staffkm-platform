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
  },

  nav: {
    chat:        '對話',
    apps:        '應用',
    knowledge:   '知識庫',
    agents:      '代理人',
    users:       '使用者',
    models:      '模型',
    settings:    '設定',
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
}
