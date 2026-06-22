import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/Login.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/auth/Register.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    component: () => import('@/components/layout/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/chat',
      },
      {
        path: 'chat',
        name: 'Chat',
        component: () => import('@/views/chat/Index.vue'),
        meta: { fullHeight: true },
      },
      {
        path: 'chat/:sessionId',
        name: 'ChatSession',
        component: () => import('@/views/chat/Index.vue'),
        props: true,
        meta: { fullHeight: true },
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/Index.vue'),
      },
      {
        path: 'tasks',
        name: 'TaskList',
        component: () => import('@/views/tasks/List.vue'),
      },
      {
        path: 'tasks/create',
        name: 'TaskCreate',
        component: () => import('@/views/tasks/Create.vue'),
      },
      {
        path: 'tasks/:id',
        name: 'TaskDetail',
        component: () => import('@/views/tasks/Detail.vue'),
        props: true,
      },
      {
        path: 'agents',
        name: 'AgentList',
        component: () => import('@/views/agents/List.vue'),
        meta: { permission: 'admin' },
      },
      {
        path: 'agents/create',
        name: 'AgentCreate',
        component: () => import('@/views/agents/Create.vue'),
        meta: { permission: 'admin' },
      },
      {
        path: 'skills',
        name: 'SkillList',
        component: () => import('@/views/skills/List.vue'),
      },
      {
        path: 'exports',
        name: 'ExportList',
        component: () => import('@/views/exports/Index.vue'),
        meta: { permission: 'admin' },
      },
      {
        path: 'settings/llm',
        name: 'LLMSettings',
        component: () => import('@/views/settings/LLMConfig.vue'),
      },
      {
        path: 'settings/profile',
        name: 'Profile',
        component: () => import('@/views/settings/Profile.vue'),
      },
      {
        path: 'settings/agent',
        name: 'AgentSettings',
        component: () => import('@/views/settings/Agent.vue'),
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫
router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()
  const requiresAuth = to.meta.requiresAuth !== false
  const permission = to.meta.permission as string | undefined

  if (requiresAuth && !authStore.token) {
    next('/login')
    return
  }

  if (permission && !authStore.hasPermission(permission)) {
    next('/dashboard')
    return
  }

  if ((to.path === '/login' || to.path === '/register') && authStore.token) {
    next('/chat')
    return
  }

  next()
})

export default router
