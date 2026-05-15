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
    {
      path: '/',
      component: () => import('../views/dashboard/DashboardLayout.vue'),
      children: [
        {
          path: '',
          redirect: '/chat',
        },
        {
          path: 'chat',
          name: 'chat',
          component: () => import('../views/chat/ChatView.vue'),
          meta: { title: '智慧問答' },
        },
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
