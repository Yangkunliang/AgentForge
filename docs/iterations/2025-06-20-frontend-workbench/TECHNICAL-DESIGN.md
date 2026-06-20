# TASK-005 技术设计

## 1. 技术栈

| 技术 | 版本 | 说明 |
|------|------|------|
| Vite | 5.x | 构建工具 |
| Vue | 3.4+ | 渐进式框架 |
| TypeScript | 5.x | 类型安全 |
| Element Plus | 2.x | UI 组件库 |
| Pinia | 2.x | 状态管理 |
| Vue Router | 4.x | 路由管理 |
| Axios | 1.x | HTTP 客户端 |
| SCSS | - | 样式预处理 |

## 2. 项目结构

```
web/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tsconfig.node.json
├── .env
├── .env.production
├── scripts/
│   └── gen-types.sh
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── api/
│   │   ├── request.ts      # Axios 实例
│   │   ├── schema.d.ts     # 自动生成类型
│   │   └── modules/
│   │       ├── auth.ts
│   │       ├── tasks.ts
│   │       ├── agents.ts
│   │       ├── skills.ts
│   │       ├── dashboard.ts
│   │       └── exports.ts
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppHeader.vue
│   │   │   ├── AppSidebar.vue
│   │   │   └── AppLayout.vue
│   │   ├── tasks/
│   │   │   ├── TaskProgress.vue
│   │   │   ├── LiveLog.vue
│   │   │   └── AgentBids.vue
│   │   └── common/
│   │       └── LoadingButton.vue
│   ├── composables/
│   │   ├── useSSE.ts
│   │   └── usePermission.ts
│   ├── directives/
│   │   └── permission.ts
│   ├── router/
│   │   └── index.ts
│   ├── stores/
│   │   ├── auth.ts
│   │   ├── task.ts
│   │   ├── agent.ts
│   │   ├── skill.ts
│   │   └── app.ts
│   ├── styles/
│   │   ├── variables.scss
│   │   └── global.scss
│   ├── types/
│   │   └── index.ts
│   └── views/
│       ├── auth/
│       │   ├── Login.vue
│       │   └── Register.vue
│       ├── dashboard/
│       │   └── Index.vue
│       ├── tasks/
│       │   ├── List.vue
│       │   ├── Create.vue
│       │   └── Detail.vue
│       ├── agents/
│       │   ├── List.vue
│       │   └── Create.vue
│       ├── skills/
│       │   ├── List.vue
│       │   └── Install.vue
│       └── exports/
│           └── Index.vue
└── public/
    └── favicon.ico
```

## 3. API 代理配置

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

## 4. SSE 客户端设计

```typescript
// useSSE.ts
export function useSSE(taskId: string) {
  const events = ref<SSEEvent[]>([])

  const connect = async () => {
    const response = await fetch(`/api/v1/tasks/${taskId}/stream`, {
      headers: { Authorization: `Bearer ${token.value}` },
    })

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value)
      // 解析 SSE 事件
      parseSSEMessage(chunk)
    }
  }

  return { events, connect, disconnect }
}
```

## 5. 状态管理设计

### auth store

```typescript
interface AuthState {
  accessToken: string | null
  user: User | null
  permissions: string[]
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token'))
  const user = ref<User | null>(null)

  async function login(credentials: LoginForm) {
    const { data } = await authApi.login(credentials)
    token.value = data.access_token
    user.value = data.user
  }

  function hasPermission(permission: string) {
    return user.value?.permissions.includes(permission)
  }

  return { token, user, login, logout, hasPermission }
})
```

### task store

```typescript
export const useTaskStore = defineStore('task', () => {
  const tasks = ref<Task[]>([])
  const currentTask = ref<Task | null>(null)
  const sseEvents = ref<SSEEvent[]>([])

  function handleSSEEvent(event: SSEEvent) {
    sseEvents.value.push(event)
    // 根据事件类型更新 UI
  }

  return { tasks, currentTask, sseEvents, handleSSEEvent }
})
```

## 6. 路由守卫

```typescript
router.beforeEach(async (to, from, next) => {
  const auth = useAuthStore()

  if (to.meta.requiresAuth && !auth.token) {
    next('/login')
    return
  }

  if (to.meta.permission && !auth.hasPermission(to.meta.permission)) {
    next('/dashboard')
    return
  }

  next()
})
```