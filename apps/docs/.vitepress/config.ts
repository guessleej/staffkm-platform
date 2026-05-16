import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'staffKM',
  description: 'Enterprise AI Knowledge Management Platform',
  lang: 'zh-TW',
  cleanUrls: true,
  themeConfig: {
    siteTitle: 'staffKM',
    logo: '/favicon.svg',
    nav: [
      { text: '使用者', link: '/user/getting-started' },
      { text: '管理者', link: '/admin/installation' },
      { text: '開發者', link: '/developer/api' },
      { text: 'GitHub', link: 'https://github.com/guessleej/staffkm-platform' },
    ],
    sidebar: {
      '/user/': [
        { text: '使用者指南', items: [
          { text: '快速開始',       link: '/user/getting-started' },
          { text: '對話與知識庫',   link: '/user/chat' },
          { text: '工作流程',       link: '/user/workflows' },
        ]},
      ],
      '/admin/': [
        { text: '管理者指南', items: [
          { text: '安裝部署',         link: '/admin/installation' },
          { text: '多租戶與 RBAC',     link: '/admin/multi-tenant' },
          { text: 'Quota 與用量',     link: '/admin/quota' },
          { text: '備份與災難復原',   link: '/admin/backup-dr' },
        ]},
      ],
      '/developer/': [
        { text: '開發者指南', items: [
          { text: 'REST API',     link: '/developer/api' },
          { text: 'Python SDK',   link: '/developer/sdk-python' },
          { text: 'CLI',          link: '/developer/cli' },
          { text: 'Webhooks',     link: '/developer/webhooks' },
        ]},
      ],
    },
    socialLinks: [
      { icon: 'github', link: 'https://github.com/guessleej/staffkm-platform' },
    ],
    footer: {
      message: 'Apache-2.0 License',
      copyright: 'Copyright © 2026 staffKM',
    },
    search: { provider: 'local' },
  },
})
