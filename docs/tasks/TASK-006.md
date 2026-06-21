# TASK-006：面向用户的对话工作台（Chat UI）

## 关联需求

| 用户故事 | 描述 |
|---------|------|
| US-1 | 作为用户，我想通过自然语言输入需求，系统自动处理并返回结果 |
| US-2 | 作为用户，我想看到 AI 实时响应的过程，而不是等待一个黑盒结果 |

> 多 Agent 编排是后端内部实现细节，对用户完全透明。本任务的目标是提供一个面向终端用户的对话界面，体验上类比 ChatGPT：用户只需输入自然语言，看到流式回复，无需感知任何"任务"、"子任务"、"Agent 分配"等概念。

## 设计原则

- **用户视角**：界面只有"会话"和"消息"，没有"任务"、"优先级"、"Agent"
- **透明执行**：多 Agent 协作过程通过 SSE 实时推送，以"AI 正在思考..."的形式呈现，不暴露内部细节
- **类比微服务**：就像高并发系统用微服务支撑性能，多 Agent 是为了提供更好的结果质量，前台体验始终是简洁的对话

## 优先级

**P2** — 依赖 TASK-003（SSE）和 TASK-002（任务 API），是用户真正使用系统的入口

## 依赖

- TASK-001：认证系统
- TASK-002：任务管理 API
- TASK-003：Harness 核心 + SSE

## 验收标准

- [x] 左侧侧边栏显示历史会话列表，可新建会话、可切换
- [x] 右侧为对话气泡界面，区分用户消息和 AI 消息
- [x] 发送消息后，AI 回复通过 SSE 流式逐字追加，有"思考中..."状态
- [x] 刷新页面后，历史消息可从后端恢复，不丢失
- [x] 会话支持命名（默认取首条消息前 20 字），可手动重命名
- [x] 移动端响应式：侧边栏可折叠，对话区全屏展示

## 技术子项

### 后端：会话与消息模型

- [x] **新增 `Session` 数据模型**（`src/agent_forge/models/session.py`）
  ```
  Session: id, user_id, title, created_at, updated_at
  Message: id, session_id, role(user/assistant), content, created_at
  ```
  - `Session` 与 `Task` 关联：一条 Message 触发一个 Task，`Message.task_id` 外键关联
  - Alembic 新增 migration

- [x] **会话 API**（`src/api/routes/sessions.py`）
  - `GET /api/v1/sessions` — 会话列表（按 updated_at 倒序）
  - `POST /api/v1/sessions` — 新建会话
  - `PATCH /api/v1/sessions/{id}` — 重命名会话
  - `DELETE /api/v1/sessions/{id}` — 删除会话（级联删除消息）
  - `GET /api/v1/sessions/{id}/messages` — 获取历史消息列表

- [x] **对话发送 API**（`src/api/routes/sessions.py`）
  - `POST /api/v1/sessions/{id}/chat`
    - 接收用户消息，写入 Message（role=user）
    - 异步创建 Task，绑定到本条 Message
    - 返回 `{ message_id, task_id }` 用于前端订阅 SSE

- [x] **SSE 接入**：`POST /sessions/{id}/chat` 触发 `executor.execute_task()`，执行过程通过已有 `emit_*` 函数推送事件；任务完成后写入 Message（role=assistant，content=结果）

### 前端：对话工作台

- [x] **路由调整**（`web/src/router/index.ts`）
  - 新增 `/chat` 和 `/chat/:sessionId` 路由
  - 登录后默认重定向到 `/chat`（而非任务列表）

- [x] **会话 Store**（`web/src/stores/session.ts`）
  - `sessions: Session[]` — 会话列表
  - `currentSession` — 当前会话
  - `messages: Message[]` — 当前会话的消息列表
  - `fetchSessions()` / `createSession()` / `deleteSession()` / `renameSession()`
  - `fetchMessages(sessionId)` / `sendMessage(content)`

- [x] **会话侧边栏**（`web/src/components/chat/SessionSidebar.vue`）
  - 顶部"新建对话"按钮
  - 会话列表（标题 + 时间，active 高亮）
  - 每条会话右键或 hover 显示重命名/删除操作
  - 与 AppSidebar 集成，或在 Chat 布局内独立实现

- [x] **对话主界面**（`web/src/views/chat/Index.vue`）
  - 消息气泡列表（用户右对齐，AI 左对齐）
  - AI 消息支持 Markdown 渲染（使用 `marked` 或 `markdown-it`）
  - 底部输入框：文本域 + 发送按钮，支持 `Ctrl+Enter` 发送
  - 消息列表自动滚动到底部

- [x] **流式打字效果**（`web/src/components/chat/AssistantMessage.vue`）
  - 发送后立即显示"思考中..."占位气泡
  - SSE `llm_response` 事件触发逐字追加内容
  - `task_completed` 事件后显示完整结果，停止流式
  - `task_failed` 事件后显示错误提示

- [x] **useChat composable**（`web/src/composables/useChat.ts`）
  - 封装"发送消息 → 获取 task_id → 订阅 SSE → 更新消息气泡"完整流程
  - 复用已有 `useSSE.ts` 的底层连接逻辑

### 前端：响应式适配

- [x] 桌面端：侧边栏固定宽度 260px，右侧对话区自适应
- [x] 移动端（< 768px）：侧边栏默认隐藏，顶部汉堡菜单展开

## 产出物

**后端：**
- `src/agent_forge/models/session.py` — Session、Message 模型
- `src/api/routes/sessions.py` — 会话和对话 API
- `migrations/alembic/versions/001_add_sessions.py` — 数据库迁移

**前端：**
- `web/src/views/chat/Index.vue` — 对话主界面
- `web/src/components/chat/SessionSidebar.vue` — 会话侧边栏
- `web/src/components/chat/AssistantMessage.vue` — 流式 AI 消息气泡
- `web/src/stores/session.ts` — 会话状态管理
- `web/src/composables/useChat.ts` — 对话逻辑 composable

## 参考文档

- `docs/tech-design/API-SPEC.md` — 接口规范
- `docs/tech-design/FRONTEND-ARCHITECTURE.md` — 前端架构
- `src/agent_forge/api/sse.py` — SSE 事件定义（`SSEEventTypes`）
- `web/src/composables/useSSE.ts` — 已有 SSE 连接逻辑
