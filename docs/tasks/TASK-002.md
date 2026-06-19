# TASK-002：任务管理 & Agent 管理 API

## 关联需求

| 用户故事 | 描述 |
|---------|------|
| US-1 | 作为全栈开发者，我想输入一个自然语言需求，让系统自动拆解任务并分派给合适的 Agent |
| US-2 | 作为全栈开发者，我想让 Agent 自动完成产品设计、UI 设计、任务拆解，减少重复性工作 |

## 优先级

**P1** — 依赖 TASK-001（认证系统），是 Harness 核心的前置 API 层

## 验收标准

- [ ] `POST /tasks` 能创建任务，返回 task_id 和初始子任务列表
- [ ] `GET /tasks` 支持分页和 status/priority 过滤
- [ ] `GET /tasks/{id}` 返回任务详情含子任务
- [ ] `POST /tasks/{id}/cancel` 能取消进行中的任务
- [ ] `POST /tasks/{id}/feedback` 能提交反馈（thumbs/rating/comment）
- [ ] Agent CRUD 全部可用，权限校验正确（创建/删除需 admin）
- [ ] 无 token 或权限不足时返回正确错误码

## 技术子项

### 任务 API（`src/api/routes/tasks.py`）

- [ ] `POST /api/v1/tasks`
  - 请求体：description、priority（low/medium/high）、expected_models
  - 写入 Task 表，状态初始为 `pending`
  - 返回 task_id、status、trace_id、sub_tasks（初始为空列表，由 Executor 填充）

- [ ] `GET /api/v1/tasks`
  - 分页：page、per_page（默认 20）
  - 过滤：status、priority
  - 返回 total + items 列表

- [ ] `GET /api/v1/tasks/{task_id}`
  - 关联查询 SubTask 表
  - 返回完整任务详情含子任务列表

- [ ] `POST /api/v1/tasks/{task_id}/cancel`
  - 仅 pending/processing 状态可取消
  - 更新状态为 cancelled

- [ ] `POST /api/v1/tasks/{task_id}/feedback`
  - 字段：thumbs（1/-1）、rating（1-5，可选）、comment（可选，≤500字）
  - 写入 TaskExecution 表的 feedback 字段

### Agent API（`src/api/routes/agents.py`）

- [ ] `POST /api/v1/agents`（需 admin 权限）
  - 字段：name、capabilities[]、model、description
  - 写入 Agent 表，status 初始为 active

- [ ] `GET /api/v1/agents`
  - 过滤：capability、status

- [ ] `PATCH /api/v1/agents/{agent_id}`（需 admin 权限）
  - 支持更新：status、capabilities、description

- [ ] `DELETE /api/v1/agents/{agent_id}`（需 admin 权限）

### 公共部分

- [ ] **权限依赖注入**（`src/middleware/auth.py`）
  - `require_permission("read")` / `require_permission("admin")` 装饰器
  - 同时支持 Bearer Token 和 X-API-Key 两种认证方式

- [ ] **Pydantic Schema**（`src/api/schemas/`）
  - TaskCreateRequest、TaskListResponse、TaskDetailResponse
  - AgentCreateRequest、AgentResponse

## 产出物

- `src/api/routes/tasks.py`
- `src/api/routes/agents.py`
- `src/api/schemas/task.py`
- `src/api/schemas/agent.py`
- `src/middleware/auth.py`（权限依赖注入）

## 参考文档

- `docs/tech-design/API-SPEC.md` 第 3、4 节
- `docs/tech-design/SECURITY.md` 第 1 节（双认证机制）
- `docs/product-design/PRD-多智能体框架-20260617.md` US-1、US-2
