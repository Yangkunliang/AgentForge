# TASK-002 产品需求文档

## 概述

TASK-002 旨在实现 AgentForge 的任务管理和 Agent 管理核心 API，为用户提供创建、查询、更新和管理任务及 Agent 的能力。

## 功能需求

### 1. 任务管理 API

#### 1.1 创建任务
- **功能描述**：用户可以创建新的任务
- **输入参数**：
  - `description`（必填）：任务描述
  - `priority`（必填）：任务优先级（low/medium/high）
- **输出**：
  - 任务 ID
  - 任务状态（默认为 pending）
  - 追踪 ID（trace_id）
  - 创建时间
- **权限要求**：需要用户认证

#### 1.2 查询任务列表
- **功能描述**：用户可以查询自己的任务列表
- **支持过滤**：
  - 按状态过滤（pending/processing/completed/failed/cancelled）
  - 按优先级过滤（low/medium/high）
- **支持分页**：
  - `page`：页码（默认 1）
  - `per_page`：每页数量（默认 20，最大 100）
- **输出**：
  - 任务总数
  - 当前页码
  - 每页数量
  - 任务列表
- **权限要求**：需要用户认证

#### 1.3 查询任务详情
- **功能描述**：用户可以查询特定任务的详细信息
- **输入参数**：
  - `task_id`：任务 ID
- **输出**：
  - 完整的任务信息
  - 子任务列表（如果有）
- **权限要求**：需要用户认证且只能查询自己的任务

#### 1.4 取消任务
- **功能描述**：用户可以取消待处理或处理中的任务
- **输入参数**：
  - `task_id`：任务 ID
- **约束**：
  - 只能取消状态为 pending 或 processing 的任务
- **权限要求**：需要用户认证且只能取消自己的任务

#### 1.5 提交任务反馈
- **功能描述**：用户可以对已完成的任务提交反馈
- **输入参数**：
  - `task_id`：任务 ID
  - `thumbs`：点赞/点踩
  - `rating`：评分（可选）
  - `comment`：评论（可选）
- **权限要求**：需要用户认证且只能对自己的任务提交反馈

### 2. Agent 管理 API

#### 2.1 创建 Agent
- **功能描述**：管理员可以创建新的 Agent
- **输入参数**：
  - `name`（必填）：Agent 名称（全局唯一）
  - `capabilities`（必填）：Agent 能力列表
  - `model`（必填）：使用的 LLM 模型名称
  - `description`（可选）：Agent 描述
- **输出**：
  - Agent ID
  - Agent 信息
- **权限要求**：需要 admin 权限

#### 2.2 查询 Agent 列表
- **功能描述**：用户可以查询可用的 Agent 列表
- **支持过滤**：
  - 按能力过滤（capability）
  - 按状态过滤（status）
- **输出**：
  - Agent 列表
- **权限要求**：需要 read 权限

#### 2.3 查询 Agent 详情
- **功能描述**：用户可以查询特定 Agent 的详细信息
- **输入参数**：
  - `agent_id`：Agent ID
- **输出**：
  - 完整的 Agent 信息
- **权限要求**：需要 read 权限

#### 2.4 更新 Agent
- **功能描述**：管理员可以更新 Agent 信息
- **输入参数**：
  - `agent_id`：Agent ID
  - 可更新的字段：capabilities、model、status、description
- **输出**：
  - 更新后的 Agent 信息
- **权限要求**：需要 admin 权限

#### 2.5 删除 Agent
- **功能描述**：管理员可以删除 Agent
- **输入参数**：
  - `agent_id`：Agent ID
- **权限要求**：需要 admin 权限

## 非功能需求

### 1. 性能要求
- API 响应时间 < 200ms（P95）
- 支持并发请求

### 2. 安全要求
- 所有 API 需要认证（除登录接口外）
- 敏感操作需要特定权限（admin 权限）
- 用户只能访问自己的任务
- Agent 名称全局唯一

### 3. 可用性要求
- API 错误码清晰
- 提供详细的错误信息
- 支持分页避免大数据量查询

### 4. 可维护性要求
- 代码结构清晰
- 完善的单元测试
- 遵循项目编码规范

## 数据模型

### Task
- `id`：任务 ID（UUID）
- `user_id`：用户 ID
- `description`：任务描述
- `status`：任务状态
- `priority`：任务优先级
- `trace_id`：追踪 ID
- `result`：任务结果
- `created_at`：创建时间
- `completed_at`：完成时间
- `sub_tasks`：子任务列表（关系）

### Agent
- `id`：Agent ID（UUID）
- `name`：Agent 名称（唯一）
- `capabilities`：能力列表（JSON）
- `model`：LLM 模型名称
- `status`：状态
- `description`：描述
- `created_at`：创建时间
- `updated_at`：更新时间

## API 端点

### 任务管理
- `POST /api/v1/tasks` - 创建任务
- `GET /api/v1/tasks` - 查询任务列表
- `GET /api/v1/tasks/{task_id}` - 查询任务详情
- `POST /api/v1/tasks/{task_id}/cancel` - 取消任务
- `POST /api/v1/tasks/{task_id}/feedback` - 提交任务反馈

### Agent 管理
- `POST /api/v1/agents` - 创建 Agent
- `GET /api/v1/agents` - 查询 Agent 列表
- `GET /api/v1/agents/{agent_id}` - 查询 Agent 详情
- `PATCH /api/v1/agents/{agent_id}` - 更新 Agent
- `DELETE /api/v1/agents/{agent_id}` - 删除 Agent

## 验收标准

1. 所有 API 端点实现完成
2. 单元测试覆盖率 > 80%
3. 所有测试通过
4. API 文档完整
5. 性能指标满足要求
6. 安全检查通过