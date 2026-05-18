import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/login/LoginView.vue'),
      meta: { public: true },
    },
    // v4.1 A: public 14-day trial signup
    {
      path: '/signup',
      name: 'signup',
      component: () => import('../views/login/SignupView.vue'),
      meta: { public: true },
    },
    // v4.6 F: account self-service flows
    {
      path: '/verify-email',
      name: 'verify-email',
      component: () => import('../views/login/VerifyEmailView.vue'),
      meta: { public: true },
    },
    {
      path: '/forgot-password',
      name: 'forgot-password',
      component: () => import('../views/login/ForgotPasswordView.vue'),
      meta: { public: true },
    },
    {
      path: '/reset-password',
      name: 'reset-password',
      component: () => import('../views/login/ResetPasswordView.vue'),
      meta: { public: true },
    },
    {
      path: '/oauth/callback/:provider',
      name: 'oauth-callback',
      component: () => import('../views/login/OAuthCallbackView.vue'),
      meta: { public: true },
    },
    // ── 對話為中心的 layout（claude.ai 風格），獨立路徑避免與 /
    //    被 DashboardLayout 的 children 互蓋（Vue Router 只認第一個 / parent）
    {
      path: '/chat',
      component: () => import('../views/chat/ChatLayout.vue'),
      children: [
        {
          path: '',
          name: 'chat',
          component: () => import('../views/chat/ChatView.vue'),
          meta: { title: '對話' },
        },
      ],
    },
    // ── 管理介面（沿用原 DashboardLayout）─────────────────────────
    {
      path: '/',
      component: () => import('../views/dashboard/DashboardLayout.vue'),
      children: [
        { path: '', redirect: '/chat' },
        {
          path: 'knowledge',
          name: 'knowledge',
          component: () => import('../views/knowledge/KnowledgeView.vue'),
          meta: { title: '知識庫管理' },
        },
        {
          path: 'knowledge/:kbId/documents',
          name: 'knowledge-documents',
          component: () => import('../views/knowledge/DocumentView.vue'),
          meta: { title: '文件管理' },
        },
        {
          path: 'knowledge/:kbId/documents/:docId/paragraphs',
          name: 'knowledge-paragraphs',
          component: () => import('../views/knowledge/ParagraphView.vue'),
          meta: { title: '段落管理' },
        },
        {
          path: 'knowledge/:kbId/hit-test',
          name: 'hit-test',
          component: () => import('../views/knowledge/HitTestView.vue'),
          meta: { title: '命中測試' },
        },
        {
          path: 'applications',
          name: 'applications',
          component: () => import('../views/application/ApplicationListView.vue'),
          meta: { title: 'AI 應用' },
        },
        {
          path: 'applications/:appId/chat',
          name: 'application-chat',
          component: () => import('../views/application/ApplicationChatView.vue'),
          meta: { title: 'AI 應用對話' },
        },
        {
          path: 'applications/:appId/workflow',
          name: 'application-workflow',
          component: () => import('../views/application/WorkflowEditorView.vue'),
          meta: { title: '工作流程編輯器' },
        },
        {
          path: 'agents',
          name: 'agents',
          component: () => import('../views/agent/AgentView.vue'),
          meta: { title: 'AI 代理人' },
        },
        // ── 新 backlog 模組（RFC-006 對標 MaxKB）─────────────────────────
        {
          path: 'tools',
          name: 'tools',
          component: () => import('../views/tool/ToolListView.vue'),
          meta: { title: '工具' },
        },
        {
          path: 'skills',
          name: 'skills',
          component: () => import('../views/skill/SkillListView.vue'),
          meta: { title: 'Skills' },
        },
        {
          path: 'data-sources',
          name: 'data-sources',
          component: () => import('../views/datasource/DataSourceListView.vue'),
          meta: { title: '資料來源' },
        },
        {
          path: 'projects',
          name: 'projects',
          component: () => import('../views/project/ProjectsView.vue'),
          meta: { title: 'Projects' },
        },
        {
          path: 'mcp/servers',
          name: 'mcp-servers',
          component: () => import('../views/mcp/McpServersView.vue'),
          meta: { title: 'MCP Servers' },
        },
        {
          path: 'triggers',
          name: 'triggers',
          component: () => import('../views/trigger/TriggersView.vue'),
          meta: { title: '排程觸發' },
        },
        {
          path: 'memories',
          name: 'memories',
          component: () => import('../views/memory/MemoriesView.vue'),
          meta: { title: '長期記憶' },
        },
        {
          path: 'admin/audit-logs',
          name: 'admin-audit-logs',
          component: () => import('../views/admin/AuditLogsView.vue'),
          meta: { title: 'Audit Log', roles: ['admin'] },
        },
        {
          path: 'admin/users',
          name: 'admin-users',
          component: () => import('../views/admin/UsersView.vue'),
          meta: { title: '使用者管理', roles: ['admin'] },
        },
        {
          path: 'admin/models',
          name: 'admin-models',
          component: () => import('../views/admin/ModelProviderView.vue'),
          meta: { title: '模型供應商', roles: ['admin'] },
        },
        {
          path: 'admin/usage',
          name: 'admin-usage',
          component: () => import('../views/admin/UsageView.vue'),
          meta: { title: 'Token 用量 / Quota', roles: ['admin'] },
        },
        {
          path: 'admin/quotas',
          name: 'admin-quotas',
          component: () => import('../views/admin/QuotaView.vue'),
          meta: { title: 'Workspace Quota 管理', roles: ['admin'] },
        },
        {
          path: 'admin/user-quotas',
          name: 'admin-user-quotas',
          component: () => import('../views/admin/UserQuotaView.vue'),
          meta: { title: '使用者 Quota 管理', roles: ['admin'] },
        },
        {
          path: 'admin/quota-alerts',
          name: 'admin-quota-alerts',
          component: () => import('../views/admin/QuotaAlertView.vue'),
          meta: { title: '配額告警', roles: ['admin'] },
        },
        {
          path: 'admin/approvals',
          name: 'admin-approvals',
          component: () => import('../views/admin/ApprovalsView.vue'),
          meta: { title: '人工核可', roles: ['admin'] },
        },
        {
          path: 'admin/run-history',
          name: 'admin-run-history',
          component: () => import('../views/admin/RunHistoryView.vue'),
          meta: { title: 'Workflow 執行紀錄', roles: ['admin'] },
        },
        {
          path: 'admin/webhook-outbox',
          name: 'admin-webhook-outbox',
          component: () => import('../views/admin/WebhookOutboxView.vue'),
          meta: { title: 'Webhook Outbox', roles: ['admin'] },
        },
        {
          path: 'admin/heartbeats',
          name: 'admin-heartbeats',
          component: () => import('../views/admin/HeartbeatsView.vue'),
          meta: { title: 'Worker Heartbeats', roles: ['admin'] },
        },
        {
          path: 'admin/billing',
          name: 'admin-billing',
          component: () => import('../views/admin/BillingView.vue'),
          meta: { title: 'Per-User Billing', roles: ['admin'] },
        },
        {
          path: 'admin/slow-queries',
          name: 'admin-slow-queries',
          component: () => import('../views/admin/SlowQueriesView.vue'),
          meta: { title: 'Slow Query Analyzer', roles: ['admin'] },
        },
        {
          path: 'usage',
          name: 'usage',
          component: () => import('../views/usage/UsageView.vue'),
          meta: { title: '當月用量' },
        },
        {
          path: 'admin/system',
          name: 'admin-system',
          component: () => import('../views/admin/SystemView.vue'),
          meta: { title: '系統設定', roles: ['admin'] },
        },
      ],
    },
    {
      path: '/share/:appId',
      name: 'public-chat',
      component: () => import('../views/application/PublicChatView.vue'),
      meta: { public: true },
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.public) return true
  if (!auth.isAuthenticated) return '/login'
  // token 存在但 user 還沒載入（首次進站 / reload）— 用 token 換回使用者資訊
  if (!auth.user) {
    await auth.init()
    if (!auth.isAuthenticated) return '/login'   // init 失敗 → token 無效
  }
  if (to.meta.roles && !auth.hasRole(to.meta.roles as string[])) return '/'
  return true
})

export default router
