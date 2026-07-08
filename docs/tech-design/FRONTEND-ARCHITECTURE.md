# 前端架构设计 (FRONTEND-ARCHITECTURE.md)

## 1. 技术栈选型

### 1.1 核心依赖

| 组件 | 选型 | 说明 |
|------|------|------|
| 框架 | Vue 3 (Composition API + `<script setup>`) | 响应式、组合式 API、更好的 TS 支持 |
| 构建工具 | Vite 5 | 快速 HMR、原生 ESM、轻量配置 |
| UI 库 | Element Plus | 管理后台组件最成熟、中文文档完善 |
| 状态管理 | Pinia | Vue 3 官方推荐、TS 友好、DevTools 支持 |
| 路由 | Vue Router 4 | 官方路由、嵌套路由、路由守卫 |
| HTTP 客户端 | Axios | 请求拦截器、取消令牌、响应拦截器 |
| 类型系统 | TypeScript 5 | 全栈类型安全、API 类型自动生成 |
| CSS 方案 | SCSS + CSS 变量 | Element Plus 主题定制、响应式断点 |
| 图标 | @element-plus/icons-vue | 官方图标库、支持自定义 SVG |

### 1.2 辅助工具

| 工具 | 用途 |
|------|------|
| unplugin-auto-import | 自动导入 Vue/Element Plus API，减少 import 语句 |
| unplugin-vue-components | 自动导入组件，无需手动注册 |
| pinia-plugin-persistedstate | Pinia 状态持久化（localStorage） |
| vueuse | 常用组合式函数集合 |
| dayjs | 轻量级日期处理 |
| markdown-it + dompurify | Markdown 渲染 + XSS 过滤（Skill.md 展示） |
| openapi-typescript | 从 FastAPI /openapi.json 自动生成 TS 类型（见第 12 节） |

---

## 2. 项目结构

```
web/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── scripts/
│   └── gen-types.sh          # 自动生成 API 类型脚本
├── env/
│   ├── .env.development
│   └── .env.production
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── env.d.ts
│   │
│   ├── api/
│   │   ├── request.ts        # Axios 实例（见第 5 节）
│   │   ├── sse.ts            # SSE 客户端（见第 6 节）
│   │   ├── types/            # 由 openapi-typescript 生成，勿手写
│   │   │   └── schema.d.ts   # 自动生成：npm run gen:types
│   │   └── modules/
│   │       ├── auth.ts
│   │       ├── tasks.ts
│   │       ├── agents.ts
│   │       ├── projects.ts    # Project / Mount / Project Session / Project Artifact API
│   │       ├── artifacts.ts   # Artifact 详情 API
│   │       ├── pipelineRuns.ts # PipelineRun / StageState API
│   │       ├── skills.ts
│   │       ├── exports.ts
│   │       └── dashboard.ts  # 仪表盘聚合数据
│   │
│   ├── assets/
│   │   ├── images/
│   │   ├── styles/
│   │   │   ├── variables.scss
│   │   │   ├── global.scss
│   │   │   └── responsive.scss
│   │   └── icons/
│   │
│   ├── components/
│   │   ├── Layout/
│   │   │   ├── AppHeader.vue
│   │   │   ├── AppSidebar.vue
│   │   │   └── AppFooter.vue
│   │   ├── Task/
│   │   │   ├── TaskCard.vue
│   │   │   ├── TaskDetail.vue
│   │   │   ├── TaskProgress.vue
│   │   │   ├── SubTaskList.vue
│   │   │   ├── AgentBids.vue
│   │   │   └── TaskFeedback.vue   # 用户反馈组件（thumbs/rating）
│   │   ├── SSE/
│   │   │   ├── EventStream.vue    # SSE 事件流展示
│   │   │   └── LiveLog.vue        # 实时日志
│   │   ├── Common/
│   │   │   ├── EmptyState.vue
│   │   │   ├── LoadingSpinner.vue
│   │   │   ├── ConfirmDialog.vue
│   │   │   ├── MarkdownRender.vue
│   │   │   └── GlobalMessage.vue  # 全局消息提示（错误/限流/成功）
│   │   └── Skills/
│   │       ├── SkillCard.vue
│   │       ├── SkillInstall.vue
│   │       └── SkillInstallProgress.vue  # 安装进度轮询组件
│   │
│   ├── composables/
│   │   ├── useAuth.ts
│   │   ├── useTask.ts
│   │   ├── useSSE.ts          # SSE 封装（见第 6 节）
│   │   ├── usePagination.ts
│   │   ├── useResponsive.ts
│   │   └── useSkillInstall.ts # Skill 安装状态轮询
│   │
│   ├── directives/
│   │   ├── v-permission.ts    # 按钮级权限（见第 9 节）
│   │   └── v-loading.ts
│   │
│   ├── router/
│   │   ├── index.ts
│   │   ├── guards.ts
│   │   └── routes.ts
│   │
│   ├── stores/
│   │   ├── index.ts
│   │   ├── modules/
│   │   │   ├── auth.ts        # 用户状态 + Token 管理
│   │   │   ├── project.ts     # 当前项目、项目列表、Mount 缓存
│   │   │   ├── artifact.ts    # Project Artifact 列表、Viewer 当前产物
│   │   │   ├── pipeline.ts    # 当前 PipelineRun、StageState mutation
│   │   │   ├── task.ts        # 任务列表/详情 + SSE 实时更新入口
│   │   │   ├── agent.ts
│   │   │   ├── skill.ts
│   │   │   └── app.ts
│   │   └── utils/
│   │       └── storage.ts
│   │
│   ├── utils/
│   │   ├── format.ts
│   │   ├── validate.ts
│   │   └── eventBus.ts
│   │
│   └── views/
│       ├── Login.vue
│       ├── Register.vue
│       ├── Dashboard.vue
│       ├── artifacts/Detail.vue # Artifact Viewer
│       ├── TaskList.vue
│       ├── TaskCreate.vue
│       ├── TaskDetail.vue     # 包含 TaskFeedback 组件
│       ├── AgentList.vue
│       ├── AgentCreate.vue
│       ├── SkillList.vue
│       ├── SkillInstall.vue
│       ├── Export.vue
│       └── 404.vue
```

TASK-016 已补充：

- `web/src/components/chat/ArtifactCard.vue`：聊天消息中的阶段产物卡片，可查看或加入上下文。
- `web/src/views/artifacts/Detail.vue`：Artifact Viewer，支持 Markdown 与 code/text 兜底渲染。
- `web/src/stores/artifact.ts`：按 Project 缓存 Artifact 列表，并维护当前 Viewer 详情。
- `web/src/api/modules/artifacts.ts`：独立 Artifact 详情接口。
- `web/src/views/projects/Index.vue`：项目卡片展示最近产物列表。

TASK-017 已补充：

- `web/src/components/chat/ConfirmCard.vue`：聊天消息区内的人工确认节点，支持确认继续、提交修改意见、终止需求。
- `web/src/api/modules/pipelineRuns.ts`：新增 `confirmStage(runId, stageId, { action, feedback })`。
- `web/src/stores/pipeline.ts`：新增 `confirmStage` action，并复用 `mutatingStageId` 标记确认请求中的阶段。
- `web/src/composables/useChat.ts`：处理 `confirm_required` / `confirm_resolved` SSE，刷新 PipelineRun 和待确认 Artifact。
- `web/src/views/chat/Index.vue`：按当前 `PipelineRun.stages[].status=waiting_confirmation` 渲染 ConfirmCard，并从 Project Artifact 缓存匹配待确认产物。

TASK-019 已补充：

- `web/src/api/modules/artifacts.ts`：新增 `previewDelivery`、`applyDelivery`、`previewGitHubDelivery`、`applyGitHubDelivery`、`previewZipDelivery`、`applyZipDelivery`、`downloadZipPackage`、`exportDeliveryReport`。
- `web/src/views/artifacts/Detail.vue`：Artifact Viewer 新增交付面板，支持本地写回、GitHub PR Delivery 与 zip 包三种模式；本地模式选择 connected local Mount、输入目标路径、预览 unified diff、确认写回；GitHub 模式选择 connected GitHub Mount、输入 base branch / 交付分支 / PR 标题，预览远程 diff 后带 `expected_base_sha` 创建 PR；zip 模式不需要 Mount，预览包结构和 sha256 后生成可下载 zip。
- `web/e2e/artifact-viewer.spec.ts`：覆盖 diff 预览、确认写回 payload、GitHub PR Delivery payload、zip 包生成和下载、Delivery report 展示和 Markdown 下载。

TASK-020 已补充：

- `DeliveryApplyPayload` 增加 `expected_target_hash`。
- Artifact Viewer 在 preview 后从 `report.target_fingerprint.sha256` 读取目标文件 hash，并在确认写回时提交给后端。
- `GitHubDeliveryApplyPayload` 增加 `expected_base_sha`。
- Artifact Viewer 在 GitHub preview 后从 `report.base_sha` 读取 base ref，并在确认创建 PR 时提交给后端。
- 如果后端返回目标文件冲突或写回失败，交付面板沿用错误区域展示可读失败原因，用户需重新预览后再确认。

TASK-025 已补充：

- Artifact Viewer 的交付方式切换增加“zip 包”，用于用户不希望写入本地目录或远程仓库时导出制品。
- zip 模式隐藏 Mount 选择器，复用目标路径输入作为包内路径；preview 展示 `package_name`、`file_count`、`package_sha256`。
- 生成成功后读取 `delivery_report.download_url` 并通过 `downloadZipPackage` 拉取 Blob，前端使用 `URL.createObjectURL` 触发浏览器下载。
- zip Delivery 的下载按钮只在当前 Artifact report 标记 `delivery_channel=zip` 且存在 `download_url` 时显示。

TASK-026 已补充：

- `web/src/api/modules/projects.ts` 新增 `createUploadMount`，使用 multipart 调用 `/projects/{project_id}/mounts/upload`。
- `web/src/views/projects/Create.vue` 的“手动上传”模式改为真实文件选择，创建 Project 后直接创建 connected Upload Mount。
- `web/src/components/chat/ContextPickerDialog.vue` 的文件源从 connected local Mount 扩展为 connected local/upload Mount。
- `web/e2e/projects.spec.ts` 覆盖项目创建时 upload mount API 调用；`web/e2e/bridge-context.spec.ts` 覆盖 ContextPicker 选择 upload manifest 文件并随 chat payload 发送 `mount_id`。

---

## 3. 路由设计

### 3.1 路由表

```typescript
const routes = [
  { path: '/login',    component: () => import('@/views/Login.vue') },
  { path: '/register', component: () => import('@/views/Register.vue') },
  {
    path: '/',
    component: () => import('@/components/Layout/AppLayout.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      { path: 'dashboard',      name: 'Dashboard',    component: () => import('@/views/Dashboard.vue'),    meta: { title: '仪表盘',     icon: 'Odometer', permission: 'read'  } },
      { path: 'tasks',          name: 'TaskList',     component: () => import('@/views/TaskList.vue'),     meta: { title: '任务列表',   icon: 'List',     permission: 'read'  } },
      { path: 'tasks/create',   name: 'TaskCreate',   component: () => import('@/views/TaskCreate.vue'),   meta: { title: '创建任务',   icon: 'Plus',     permission: 'write' } },
      { path: 'tasks/:id',      name: 'TaskDetail',   component: () => import('@/views/TaskDetail.vue'),   meta: { title: '任务详情',   icon: 'Document', permission: 'read'  } },
      { path: 'agents',         name: 'AgentList',    component: () => import('@/views/AgentList.vue'),    meta: { title: 'Agent 管理', icon: 'Cpu',      permission: 'read'  } },
      { path: 'agents/create',  name: 'AgentCreate',  component: () => import('@/views/AgentCreate.vue'),  meta: { title: '创建 Agent', icon: 'Plus',     permission: 'admin' } },
      { path: 'skills',         name: 'SkillList',    component: () => import('@/views/SkillList.vue'),    meta: { title: 'Skill 管理', icon: 'Tool',     permission: 'read'  } },
      { path: 'skills/install', name: 'SkillInstall', component: () => import('@/views/SkillInstall.vue'), meta: { title: '安装 Skill', icon: 'Download', permission: 'admin' } },
      { path: 'exports',        name: 'Export',       component: () => import('@/views/Export.vue'),       meta: { title: '数据导出',   icon: 'Download', permission: 'admin' } },
    ],
  },
  { path: '/:pathMatch(.*)*', component: () => import('@/views/404.vue') },
]
```

### 3.2 路由守卫

```typescript
// router/guards.ts
router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()

  // 1. 无需认证的页面直接放行
  if (!to.meta.requiresAuth) return next()

  // 2. 未登录跳转登录页，保存 redirect 参数
  if (!authStore.isLoggedIn) return next(`/login?redirect=${to.fullPath}`)

  // 3. Token 快要过期（< 5 分钟）则静默刷新
  if (authStore.tokenExpiresInSec < 300) {
    const ok = await authStore.silentRefresh()
    if (!ok) return next(`/login?redirect=${to.fullPath}`)
  }

  // 4. 权限检查
  const required = to.meta.permission as string | undefined
  if (required && !authStore.hasPermission(required)) {
    return next('/dashboard')
  }

  // 5. 更新页面 title
  document.title = to.meta.title ? `${to.meta.title} - AgentForge` : 'AgentForge'

  next()
})
```

---

## 4. 状态管理 (Pinia)

### 4.1 认证状态 (auth.ts)

```typescript
export const useAuthStore = defineStore('auth', () => {
  const user           = ref<User | null>(null)
  const accessToken    = ref('')
  const tokenExpiresAt = ref(0)   // Unix timestamp（秒）

  // permissions 示例：['read'] | ['read','write'] | ['read','write','admin']
  const permissions = ref<string[]>([])

  const isLoggedIn       = computed(() => !!accessToken.value && Date.now() / 1000 < tokenExpiresAt.value)
  const tokenExpiresInSec = computed(() => tokenExpiresAt.value - Date.now() / 1000)
  const hasPermission    = (p: string) => permissions.value.includes(p) || permissions.value.includes('admin')

  async function login(username: string, password: string) {
    const res = await loginApi({ username, password })
    // access_token 存内存（+ localStorage 通过 persist）
    accessToken.value    = res.access_token
    tokenExpiresAt.value = Date.now() / 1000 + res.expires_in
    user.value           = res.user
    permissions.value    = res.user.permissions
    // refresh_token 由后端 Set-Cookie: HttpOnly 自动写入，JS 不需要处理
  }

  async function silentRefresh(): Promise<boolean> {
    try {
      // withCredentials: true 让浏览器自动带上 HttpOnly Cookie 中的 refresh_token
      const res = await refreshTokenApi()
      accessToken.value    = res.access_token
      tokenExpiresAt.value = Date.now() / 1000 + res.expires_in
      return true
    } catch {
      return false
    }
  }

  function logout() {
    accessToken.value    = ''
    tokenExpiresAt.value = 0
    user.value           = null
    permissions.value    = []
    // 调用后端 /auth/logout 让服务端清除 refresh_token Cookie
    logoutApi().catch(() => {})
  }

  return { user, accessToken, tokenExpiresAt, isLoggedIn, tokenExpiresInSec, permissions, hasPermission, login, silentRefresh, logout }
}, { persist: { paths: ['accessToken', 'tokenExpiresAt', 'permissions', 'user'] } })
```

### 4.2 项目状态 (project.ts)

TASK-014 后，Project 是前端工作台的首要上下文源，项目列表、当前项目、Mount 缓存统一由 `useProjectStore` 管理。

```typescript
export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const currentProjectId = ref<string | null>(localStorage.getItem('agentforge.current_project_id'))
  const mountsByProject = ref<Record<string, ProjectMount[]>>({})

  const currentProject = computed(() =>
    projects.value.find(project => project.id === currentProjectId.value) ?? null
  )

  async function fetchProjects() {
    const { data } = await projectsApi.list()
    projects.value = data
    reconcileCurrentProject()
  }

  async function selectProject(projectId: string) {
    currentProjectId.value = projectId
    localStorage.setItem('agentforge.current_project_id', projectId)
  }

  async function createProject(form: CreateProjectForm) { ... }
  async function fetchProjectMounts(projectId: string) { ... }
  async function createMount(projectId: string, form: CreateProjectMountForm) { ... }

  return { projects, currentProjectId, currentProject, mountsByProject, fetchProjects, selectProject, createProject, fetchProjectMounts, createMount }
})
```

规则：

- `/projects`、`/projects/create`、`ProjectBar` 不保留静态 mock 项目。
- 当前项目 ID 使用 `localStorage: agentforge.current_project_id` 恢复；若对应项目不存在，回退到项目列表第一项。
- 创建项目时同时创建 primary Mount，记录用户主动授权的本地路径、GitHub URL 或上传占位。
- TASK-018 后，`projectsApi` 新增 Bridge status、Mount 文件列表和文件读取 API；`ContextPickerDialog` 只展示当前项目 connected local Mount 的文件。
- `ContextFile` 支持 `mount_id`，聊天 payload 中的 `context_files[type=file].mount_id` 表示该文件来自用户授权 Mount，后端会读取真实内容；没有 `mount_id` 的 file 仍只是手填路径线索。
- `SessionStore` 新建和读取会话时优先使用 `currentProjectId`，调用 `/projects/{project_id}/sessions`。

### 4.3 Pipeline 状态 (pipeline.ts)

TASK-015 后，阶段预览不再只依赖前端静态配置。`usePipelineStore` 持有当前会话的 `PipelineRun`，并通过后端 API 进行阶段状态变更。

```typescript
export const usePipelineStore = defineStore('pipeline', () => {
  const currentRun = ref<PipelineRun | null>(null)
  const loading = ref(false)
  const mutatingStageId = ref<string | null>(null)

  async function fetchRun(runId: string) { ... }
  async function createForSession(sessionId: string, intentType?: ChatIntentType | null, stageOverrides?: Record<string, boolean>) { ... }
  async function skipStage(stageId: string) { ... }
  async function restoreStage(stageId: string) { ... }
  async function startStage(stageId: string) { ... }
  async function completeStage(stageId: string) { ... }

  return { currentRun, loading, mutatingStageId, fetchRun, createForSession, skipStage, restoreStage, startStage, completeStage }
})
```

规则：

- Chat 进入已有 Session 时，如果 `current_pipeline_run_id` 存在，立即拉取 `GET /pipeline-runs/{run_id}`。
- `POST /sessions/{id}/chat` 响应中的 `pipeline_run_id` 会同步回 SessionStore 并拉取当前 run。
- StagePreview 在有 `PipelineRun` 时以 `PipelineStageState` 为唯一状态源；没有 run 时才使用 `usePipeline.ts` 做发送前预览。
- optional 阶段的 skip/restore 通过后端 API 落库，刷新页面后状态不丢。
- `pipeline_started`、`stage_started`、`stage_completed`、`stage_skipped` SSE 事件触发 `fetchRun()`，保持阶段条与运行态同步。

### 4.4 任务状态 (task.ts)

SSE 收到的实时事件**直接更新 task store**，不另建 stream store，避免双重维护。

```typescript
export const useTaskStore = defineStore('task', () => {
  const taskList    = ref<TaskSummary[]>([])
  const currentTask = ref<TaskDetail | null>(null)
  const subTasks    = ref<SubTask[]>([])
  const loading     = ref(false)
  const pagination  = reactive({ page: 1, pageSize: 20, total: 0 })

  // SSE 事件处理入口（由 useSSE composable 调用）
  function handleSSEEvent(event: SSEEvent) {
    switch (event.type) {
      case 'task_started':
        if (currentTask.value?.task_id === event.data.task_id)
          currentTask.value.status = 'processing'
        break
      case 'sub_task_created':
        subTasks.value.push(event.data)
        break
      case 'bid_received': {
        const st = subTasks.value.find(s => s.id === event.data.sub_task_id)
        if (st) st.bids = event.data.bids
        break
      }
      case 'agent_selected': {
        const st = subTasks.value.find(s => s.id === event.data.sub_task_id)
        if (st) st.assigned_agent_id = event.data.agent_id
        break
      }
      case 'sub_task_completed': {
        const st = subTasks.value.find(s => s.id === event.data.sub_task_id)
        if (st) { st.status = 'completed'; st.result = event.data.result }
        break
      }
      case 'task_completed':
      case 'task_failed':
        if (currentTask.value?.task_id === event.data.task_id) {
          currentTask.value.status = event.type === 'task_completed' ? 'completed' : 'failed'
          currentTask.value.result = event.data.result
        }
        break
    }
  }

  async function fetchTasks(params?: TaskListParams) { ... }
  async function fetchTaskDetail(taskId: string) { ... }
  async function createTask(data: TaskCreateRequest) { ... }
  async function cancelTask(taskId: string) { ... }
  async function submitFeedback(taskId: string, feedback: TaskFeedback) { ... }

  return { taskList, currentTask, subTasks, loading, pagination, handleSSEEvent, fetchTasks, fetchTaskDetail, createTask, cancelTask, submitFeedback }
})
```

### 4.5 Skill 状态 (skill.ts)

```typescript
export const useSkillStore = defineStore('skill', () => {
  const skills     = ref<Skill[]>([])
  // 支持多个 Skill 同时安装，key 为 skill_name
  const installJobs = ref<Record<string, SkillInstallJob>>({})
  // SkillInstallJob: { skillName, status: 'pending'|'installing'|'done'|'failed', log: string }

  async function installSkill(source: string) { ... }
  async function pollInstallStatus(installId: string, skillName: string) { ... }
  async function fetchSkills() { ... }
  async function uninstallSkill(name: string) { ... }

  return { skills, installJobs, installSkill, pollInstallStatus, fetchSkills, uninstallSkill }
})
```

---

## 5. Token 管理策略（统一方案）

### 5.1 决策：access_token 存 localStorage，refresh_token 存 HttpOnly Cookie

| Token | 存储 | 理由 |
|-------|------|------|
| `access_token` | Pinia 内存 + localStorage（持久化） | Axios 拦截器需要读取并写入 Bearer Header，必须 JS 可访问 |
| `refresh_token` | HttpOnly Cookie（后端 Set-Cookie） | 有效期长（7d），JS 不可读，防 XSS 窃取；刷新时浏览器自动携带 |

**为什么不全部用 HttpOnly Cookie：** 若 access_token 也放 HttpOnly Cookie，Axios 无法读取，就无法构造 `Authorization: Bearer` Header；需要完全改为 Cookie 认证模式，与 API Key（X-API-Key Header）的共存方案冲突，后端中间件也要大改。

**XSS 缓解措施：**
- CSP Header（后端/Nginx 配置）：`script-src 'self'`，阻止注入脚本
- HTTPS 强制（生产环境）
- `access_token` 有效期短（1h），即使泄露影响有限
- `refresh_token` 在 HttpOnly Cookie 中，XSS 无法读取

### 5.2 Axios 配置 (api/request.ts)

```typescript
const request = axios.create({
  baseURL: '/api/v1',
  timeout: 30_000,
})

// 请求拦截器：附加 access_token
request.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 并发 401 的队列管理
let isRefreshing = false
let waitingQueue: Array<(token: string) => void> = []

// 响应拦截器：401 自动续期 + 并发安全
request.interceptors.response.use(
  res => res,
  async err => {
    const config = err.config
    // auth 接口本身不做自动续期（防止死循环）
    if (config?.authEndpoint) return Promise.reject(err)

    if (err.response?.status === 401 && !config._retry) {
      config._retry = true

      if (isRefreshing) {
        // 其他并发请求排队等待新 token
        return new Promise(resolve => {
          waitingQueue.push((token: string) => {
            config.headers.Authorization = `Bearer ${token}`
            resolve(request(config))
          })
        })
      }

      isRefreshing = true
      // 浏览器自动携带 HttpOnly Cookie 中的 refresh_token
      const res = await axios.post('/api/v1/auth/refresh', {}, { withCredentials: true })
      const newToken = res.data.access_token
      localStorage.setItem('access_token', newToken)
      isRefreshing = false

      // 通知队列中所有等待请求一并重试
      waitingQueue.forEach(cb => cb(newToken))
      waitingQueue = []

      // 重试原始请求
      config.headers.Authorization = `Bearer ${newToken}`
      return request(config)
    }

    // refresh 失败 → 清除 token 跳登录
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token')
      router.push('/login')
    }

    handleApiError(err.response?.status, err.response?.data?.error)
    return Promise.reject(err)
  }
)

function handleApiError(status: number, error?: { code: string; message: string }) {
  if (status === 429) {
    ElMessage.warning('操作过于频繁，请稍后再试')
  } else if (status >= 500) {
    ElMessage.error(`服务器错误：${error?.message ?? '请稍后重试'}`)
  } else if (status && status >= 400 && status !== 401) {
    ElMessage.error(error?.message ?? '请求失败')
  }
}
```

**并发续期流程：**
```
请求 A 401 → isRefreshing=true → 调 /auth/refresh → 得到新 token
请求 B 401 → isRefreshing=true → 进入 waitingQueue 排队
请求 C 401 → isRefreshing=true → 进入 waitingQueue 排队
                               ↓
refresh 完成 → 通知队列 → B、C 自动重试，用户无感知
```

---

## 6. SSE 流式订阅（统一方案）

### 6.1 决策：使用 fetch + ReadableStream，不使用原生 EventSource

原生 `EventSource` 不支持自定义 Header，无法携带 `Authorization: Bearer <token>`。使用 `fetch + ReadableStream` 可完全控制请求头，同时实现指数退避重连。

### 6.2 useSSE composable (composables/useSSE.ts)

```typescript
export function useSSE(taskId: string) {
  const taskStore = useTaskStore()
  const authStore = useAuthStore()
  const events    = ref<SSEEvent[]>([])
  const connected = ref(false)
  const error     = ref<string | null>(null)

  let controller: AbortController | null = null
  let retryTimer: ReturnType<typeof setTimeout> | null = null
  let retryCount = 0
  const MAX_RETRY = 5

  async function connect() {
    controller   = new AbortController()
    connected.value = true
    error.value  = null

    try {
      const res = await fetch(`/api/v1/tasks/${taskId}/stream`, {
        headers: {
          'Authorization': `Bearer ${authStore.accessToken}`,
          'Accept': 'text/event-stream',
          'Cache-Control': 'no-cache',
        },
        signal: controller.signal,
      })

      if (!res.ok || !res.body) throw new Error(`SSE 连接失败: ${res.status}`)

      const reader = res.body.pipeThrough(new TextDecoderStream()).getReader()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += value
        // SSE 消息以两个换行符分隔
        const chunks = buffer.split('\n\n')
        buffer = chunks.pop() ?? ''
        for (const chunk of chunks) {
          const parsed = parseSSEChunk(chunk)
          if (!parsed) continue
          events.value.push(parsed)
          taskStore.handleSSEEvent(parsed)   // 同步到 task store
          if (parsed.type === 'task_completed' || parsed.type === 'task_failed') {
            disconnect()
            return
          }
        }
      }
      retryCount = 0   // 正常结束，重置重试计数
    } catch (e: any) {
      if (e.name === 'AbortError') return   // 主动断开，不重连
      connected.value = false
      error.value = e.message
      scheduleRetry()
    }
  }

  function scheduleRetry() {
    if (retryCount >= MAX_RETRY) {
      error.value = 'SSE 连接超过最大重试次数，请刷新页面'
      return
    }
    const delay = Math.min(1000 * 2 ** retryCount, 30_000)   // 指数退避，最大 30s
    retryTimer = setTimeout(() => { retryCount++; connect() }, delay)
  }

  function parseSSEChunk(chunk: string): SSEEvent | null {
    const lines = chunk.trim().split('\n')
    let type = '', data = ''
    for (const line of lines) {
      if (line.startsWith('event:')) type = line.slice(6).trim()
      if (line.startsWith('data:'))  data = line.slice(5).trim()
    }
    if (!type || !data) return null
    try { return { type, data: JSON.parse(data) } }
    catch { return null }
  }

  function disconnect() {
    controller?.abort()
    if (retryTimer) clearTimeout(retryTimer)
    connected.value = false
  }

  onMounted(() => connect())
  onUnmounted(() => disconnect())

  return { events, connected, error, disconnect }
}
```

---

## 7. 权限模型

### 7.1 权限分级

| 权限级别 | permissions 值 | 可访问功能 |
|---------|--------------|-----------|
| `read`  | `["read"]` | 查看任务/Agent/Skill 列表、Dashboard、任务详情 |
| `write` | `["read", "write"]` | 以上 + 创建/取消任务、提交反馈 |
| `admin` | `["read", "write", "admin"]` | 以上 + 注册 Agent、安装/卸载 Skill、数据导出 |

### 7.2 权限来源

登录响应中返回 `user.permissions`，存入 auth store：

```json
{
  "access_token": "eyJ...",
  "expires_in": 3600,
  "user": {
    "id": "user-001",
    "username": "admin",
    "permissions": ["read", "write", "admin"]
  }
}
```

注意：`refresh_token` 不在响应 body 中，由后端通过 `Set-Cookie: refresh_token=...; HttpOnly; SameSite=Lax; Path=/api/v1/auth` 写入浏览器。

### 7.3 路由级权限

路由 `meta.permission` 声明所需最低权限，路由守卫校验（见第 3.2 节）。无权限时跳 Dashboard，侧边栏菜单根据权限动态过滤（无权限的菜单项不展示）。

### 7.4 按钮级权限 (v-permission 指令)

```typescript
// directives/v-permission.ts
export const vPermission: Directive = {
  mounted(el: HTMLElement, binding: DirectiveBinding<string>) {
    const { hasPermission } = useAuthStore()
    if (!hasPermission(binding.value)) {
      el.style.display = 'none'   // 隐藏，避免 layout 抖动
    }
  },
  updated(el: HTMLElement, binding: DirectiveBinding<string>) {
    const { hasPermission } = useAuthStore()
    el.style.display = hasPermission(binding.value) ? '' : 'none'
  }
}

// 使用示例
// <el-button v-permission="'admin'" @click="handleInstall">安装 Skill</el-button>
// <el-button v-permission="'write'" @click="handleCreate">创建任务</el-button>
```

---

## 8. Dashboard 数据源

Dashboard.vue 展示聚合数据，对应后端 `GET /api/v1/dashboard`（见 API-SPEC 第 9 节）。

| 卡片/图表 | 数据字段 | 说明 |
|---------|---------|------|
| 任务总览 | `tasks.total / pending / processing / completed / failed` | 今日任务状态分布 |
| Agent 状态 | `agents.active / inactive` | 在线/离线 Agent 数 |
| Skill 数量 | `skills.total` | 已安装 Skill 数 |
| 今日费用 | `cost.today_usd / trend_pct` | LLM 调用费用 + 环比百分比 |
| 最近任务 | `recent_tasks[]` | 最近 5 条任务（含状态、费用） |
| 费用趋势折线图 | `cost.daily_7d[]` | 近 7 天每日费用 |

```typescript
// api/modules/dashboard.ts
export interface DashboardData {
  tasks: { total: number; pending: number; processing: number; completed: number; failed: number }
  agents: { active: number; inactive: number }
  skills: { total: number }
  cost: {
    today_usd: number
    trend_pct: number   // 正数=增加，负数=减少，相对昨日
    daily_7d: Array<{ date: string; usd: number }>
  }
  recent_tasks: TaskSummary[]
}

export function getDashboard(): Promise<DashboardData> {
  return request.get('/dashboard')
}
```

---

## 9. Skill 安装 UI 流程

Skill 安装为异步操作（需执行 pip install），前端通过轮询获取进度：

```
用户提交 → POST /skills/install
    │ 返回 { install_id, skill_name, status: 'pending' }
    ▼
useSkillInstall composable 每 2s 轮询
    GET /skills/install/{install_id}
    │ status: 'installing' → SkillInstallProgress.vue 追加日志
    │ status: 'done'       → ElMessage.success，刷新 Skill 列表
    │ status: 'failed'     → ElMessage.error，展示错误详情
```

```typescript
// composables/useSkillInstall.ts
export function useSkillInstall() {
  const skillStore = useSkillStore()

  async function install(source: string) {
    const { install_id, skill_name } = await installSkillApi({ source })
    skillStore.installJobs[skill_name] = { skillName: skill_name, status: 'installing', log: '' }
    poll(install_id, skill_name)
  }

  function poll(installId: string, skillName: string) {
    const timer = setInterval(async () => {
      const res = await getInstallStatusApi(installId)
      skillStore.installJobs[skillName].log    = res.log ?? ''
      skillStore.installJobs[skillName].status = res.status
      if (res.status === 'done') {
        clearInterval(timer)
        ElMessage.success(`${skillName} 安装成功`)
        await skillStore.fetchSkills()
      } else if (res.status === 'failed') {
        clearInterval(timer)
        ElMessage.error(`${skillName} 安装失败：${res.error}`)
      }
    }, 2000)
  }

  return { install }
}
```

---

## 10. 错误处理 UX 规范

| 场景 | 展示方式 | 行为 |
|------|---------|------|
| 表单校验失败 | `ElForm` 内联错误 | 字段级红色提示，不弹全局 message |
| API 4xx 业务错误 | `ElMessage.error` | 顶部弹出 3s，展示 error.message |
| 429 限流 | `ElMessage.warning` | "操作过于频繁，请稍后再试" |
| API 5xx 服务器错误 | `ElMessage.error` | 展示错误信息，组件内提供重试按钮 |
| SSE 断线重连中 | `LiveLog.vue` 内 Banner | 展示"连接中断，X 秒后重连..." |
| SSE 超过最大重试 | `LiveLog.vue` 内 Alert | 展示"连接失败，请刷新页面" + 刷新按钮 |
| Token 过期刷新失败 | 跳转 `/login?redirect=...` | 登录成功后回跳原页面 |

**约定：所有全局 ElMessage 调用统一在 `api/request.ts` 响应拦截器中处理，业务代码中不重复调用，避免重复提示。**

---

## 11. API 类型自动生成

> 禁止手写 API 类型，从后端 OpenAPI Schema 自动生成，保证前后端类型同步。

```bash
# scripts/gen-types.sh（后端须先在 localhost:8000 启动）
npx openapi-typescript http://localhost:8000/openapi.json -o src/api/types/schema.d.ts
```

```json
// package.json scripts
{
  "gen:types": "bash scripts/gen-types.sh"
}
```

```typescript
// 在 API 模块中引用
import type { components } from '@/api/types/schema'
type Task            = components['schemas']['Task']
type TaskCreateReq   = components['schemas']['TaskCreateRequest']
type DashboardData   = components['schemas']['DashboardResponse']
```

**约定：`src/api/types/schema.d.ts` 不允许手动修改，后端 Schema 变更后执行 `npm run gen:types` 重新生成。**

---

## 12. 主题与样式

### 12.1 Element Plus 主题定制

```scss
:root {
  --el-color-primary: #409EFF;
  --el-color-success: #67C23A;
  --el-color-warning: #E6A23C;
  --el-color-danger:  #F56C6C;
  --el-color-info:    #909399;
  --sidebar-width:    220px;
  --header-height:    60px;
  --page-padding:     24px;
}
```

### 12.2 全局布局

```
┌──────────────────────────────────────────────┐
│                   AppHeader                   │  60px
├────────┬─────────────────────────────────────┤
│App     │           Main Content              │
│Sidebar │      padding: var(--page-padding)   │
│ 220px  │                                     │
├────────┴─────────────────────────────────────┤
│                 AppFooter                     │  40px
└──────────────────────────────────────────────┘
```

---

## 13. 响应式策略

### 13.1 断点定义

```scss
$breakpoints: (
  xs: 480px,
  sm: 768px,
  md: 1024px,
  lg: 1280px,
  xl: 1536px,
);
```

### 13.2 响应式行为

| 断点 | 侧边栏 | 布局 | 表格 |
|------|--------|------|------|
| `< 768px` | 隐藏（抽屉式） | 单列 | 堆叠/横向滚动 |
| `768px–1024px` | 折叠（图标模式） | 双列 | 紧凑模式 |
| `> 1024px` | 展开 | 标准 | 标准模式 |

---

## 14. Vite 配置

```typescript
export default defineConfig({
  plugins: [
    vue(),
    autoImport({ imports: ['vue', 'vue-router', 'pinia'] }),
    components({ dirs: ['src/components'] }),
  ],
  resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
  server: {
    port: 3000,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
  build: { target: 'es2020', outDir: 'dist', sourcemap: false },
})
```

---

## 15. 与后端集成

| 环境 | 前端 | 后端 | 跨域处理 |
|------|------|------|---------|
| 开发 | `localhost:3000` | `localhost:8000` | Vite proxy 转发 `/api` |
| 生产 | `localhost:8080` (Nginx) | `localhost:8000` (Nginx 反向代理) | 同域，无需跨域 |

---

## 16. 开发工作流

```bash
npm install        # 安装依赖
npm run dev        # 开发服务器（localhost:3000）
npm run gen:types  # 同步后端 API 类型（后端须先启动）
npm run build      # 生产构建 → dist/
npm run preview    # 本地预览构建结果
npm run lint       # ESLint + StyleLint
```
