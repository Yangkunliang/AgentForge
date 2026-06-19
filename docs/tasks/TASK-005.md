# TASK-005：前端工作台 & UI/UX 体验

## 关联需求

| 用户故事 | 描述 |
|---------|------|
| US-1 | 作为全栈开发者，我想输入一个自然语言需求，让系统自动拆解任务并分派给合适的 Agent |
| US-2 | 作为全栈开发者，我想让 Agent 自动完成产品设计、UI 设计、任务拆解，减少重复性工作 |
| US-3 | 作为全栈开发者，我想快速导入新的 Skill 插件，扩展 Agent 能力 |
| US-4 | 作为全栈开发者，我想导出训练数据，优化我的模型和 Agent 路由 |
| US-5 | 作为全栈开发者，我想看到安全的 API 调用记录，以便审计和合规 |

## 优先级

**P3** — 依赖后端 API、SSE 事件、Skill API、Dashboard/Export API 稳定后实现；UI 设计可在接口稳定前先行。

## Skill 使用约束

前端 UI/UX 设计阶段允许使用本地 `~/.claude/skills/ui-ux-pro-max`，但仅作为 advisory skill：

- 仅用于 UI design、UX review、design system、frontend visual spec。
- 输出必须沉淀到 `UI-DESIGN.md` 或 `UI-REVIEW.md`。
- 不得参与后端、数据库、安全、部署、Agent 编排或核心领域模型决策。
- 不在执行中动态下载或自动更新该 skill。

## 验收标准

- [ ] 用户能注册、登录、退出，Token 刷新和权限路由行为正确。
- [ ] 用户能创建任务、查看任务列表、查看任务详情和提交反馈。
- [ ] 任务详情页能通过 SSE 展示任务拆解、Agent 竞标、Skill 调用、结果合并等实时事件。
- [ ] Agent 管理页能展示、创建、更新和删除 Agent，admin 权限校验正确。
- [ ] Skill 管理页能安装 Skill、查看安装进度、查看已安装列表和卸载。
- [ ] Dashboard 展示任务统计、Agent 状态、Skill 数量、费用趋势和最近任务。
- [ ] Export 页面能发起导出、查看状态、下载 JSONL 文件。
- [ ] 前端类型通过 OpenAPI 自动生成，不手写 API 响应类型。
- [ ] UI 风格符合开发者工具定位：专业、克制、可扫描、信息密度适中。
- [ ] 移动端和桌面端关键页面无文本溢出、控件重叠或不可操作状态。

## 技术子项

### UI/UX 设计产物

- [ ] **UI-DESIGN.md**
  - 信息架构：Dashboard、任务、Agent、Skill、Export、Auth。
  - 页面结构：每个页面的核心区域、表格、表单、状态区和操作入口。
  - 组件清单：布局、导航、任务进度、实时日志、安装进度、反馈组件。
  - 响应式规则：桌面、平板、移动端布局变化。
  - 视觉约束：Element Plus 风格基础上保持开发者工具气质。

- [ ] **UI-REVIEW.md**（可选）
  - 使用本地 `ui-ux-pro-max` 做 UI/UX review 后输出。
  - 只记录建议、风险和调整项，不直接改写系统架构。

### 前端项目骨架（`web/`）

- [ ] Vite 5 + Vue 3 + TypeScript 5 + Element Plus + Pinia + Vue Router 4。
- [ ] `vite.config.ts` 配置 `/api` 代理到 `localhost:8000`。
- [ ] SCSS + CSS 变量组织基础主题。
- [ ] `@element-plus/icons-vue` 用于导航和按钮图标。

### API 层

- [ ] **Axios 实例**（`web/src/api/request.ts`）
  - 注入 Bearer Token。
  - 401 时尝试 silent refresh。
  - 429/5xx 统一错误提示。
  - 请求取消和超时处理。

- [ ] **API 模块**（`web/src/api/modules/`）
  - `auth.ts`
  - `tasks.ts`
  - `agents.ts`
  - `skills.ts`
  - `exports.ts`
  - `dashboard.ts`

- [ ] **类型生成**
  - `scripts/gen-types.sh` 从 FastAPI `/openapi.json` 生成 `schema.d.ts`。
  - `package.json` 添加 `gen:types` 脚本。

### 状态管理

- [ ] **auth store**
  - access_token、expires_at、user、permissions。
  - `login()`、`logout()`、`silentRefresh()`、`hasPermission()`。

- [ ] **task store**
  - 任务列表、任务详情、分页状态。
  - `handleSSEEvent()` 统一消费 SSE 事件并更新 UI。

- [ ] **agent / skill / app store**
  - Agent 列表和筛选。
  - Skill 安装状态和轮询。
  - 全局加载、错误和侧边栏状态。

### SSE 客户端

- [ ] `useSSE.ts` 使用 `fetch + ReadableStream`，不用原生 `EventSource`。
- [ ] 请求头携带 Bearer Token。
- [ ] 支持指数退避重连，最多 5 次，最大 30s。
- [ ] 支持主动关闭，离开任务详情页时清理连接。
- [ ] 解析事件并分发给 `taskStore.handleSSEEvent()`。

### 页面与组件

- [ ] **Auth**
  - `Login.vue`
  - `Register.vue`

- [ ] **Dashboard**
  - 任务状态分布。
  - 费用趋势。
  - Agent/Skill 状态总览。
  - 最近任务列表。

- [ ] **Tasks**
  - `TaskList.vue`
  - `TaskCreate.vue`
  - `TaskDetail.vue`
  - `TaskProgress.vue`
  - `SubTaskList.vue`
  - `AgentBids.vue`
  - `LiveLog.vue`
  - `TaskFeedback.vue`

- [ ] **Agents**
  - `AgentList.vue`
  - `AgentCreate.vue`
  - Agent 状态和 capability 筛选。

- [ ] **Skills**
  - `SkillList.vue`
  - `SkillInstall.vue`
  - `SkillInstallProgress.vue`

- [ ] **Exports**
  - `Export.vue`
  - 导出状态和下载入口。

### 权限与可访问性

- [ ] 路由守卫检查登录状态、Token 过期和页面权限。
- [ ] `v-permission` 控制按钮级权限。
- [ ] 表单错误信息明确可读。
- [ ] 键盘可达，关键操作有 loading/disabled 状态。
- [ ] 文本在移动端和桌面端不溢出。

## 产出物

- `docs/iterations/<date>-frontend-workbench/UI-DESIGN.md`
- `web/package.json`
- `web/vite.config.ts`
- `web/src/main.ts`
- `web/src/api/**`
- `web/src/stores/**`
- `web/src/composables/useSSE.ts`
- `web/src/router/**`
- `web/src/views/**`
- `web/src/components/**`
- `web/scripts/gen-types.sh`

## 参考文档

- `docs/tech-design/FRONTEND-ARCHITECTURE.md`
- `docs/tech-design/API-SPEC.md`
- `docs/standards/ITERATION-STANDARD.md` 第 6、7 节
- `docs/product-design/PRD-多智能体框架-20260617.md` US-1 到 US-5
