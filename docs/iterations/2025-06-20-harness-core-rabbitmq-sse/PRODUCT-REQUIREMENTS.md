# TASK-003 产品需求文档

## 概述

TASK-003 旨在实现 AgentForge 的核心执行引擎（Harness），包括任务分解、Agent 协作、消息队列、流式输出和治理机制。这是框架的核心价值所在，将实现从自然语言需求到自动化任务执行的完整流程。

## 功能需求

### 1. RabbitMQ 消息总线

#### 1.1 Exchange 和 Queue 初始化
- **功能描述**：初始化消息队列拓扑结构
- **Exchange 类型**：
  - `task.broadcast`（fanout）：用于广播招标消息
  - `task.direct`（direct）：用于定向消息传递
  - `task.dlx`（direct）：死信交换器
- **Queue 类型**：
  - `orchestrator.inbox`：编排器接收队列（TTL 60s + 死信）
  - `task.dlq`：死信队列
- **幂等性**：多次运行安全，不会重复创建

#### 1.2 消息发布和消费
- **功能描述**：实现消息的发布和消费机制
- **消息类型**：
  - `BID_ANNOUNCEMENT`：招标公告
  - `BID_RESPONSE`：竞标响应
  - `TASK_ASSIGNMENT`：任务分配
  - `TASK_RESULT`：任务结果
- **消息格式**：JSON，包含 trace_id、task_id、timestamp 等元数据

### 2. Harness 六层架构

#### 2.1 Layer 1 - Validator（验证器）
- **功能描述**：对用户输入进行验证和隔离
- **验证内容**：
  - Pydantic Schema 二次校验
  - 任务描述长度限制
  - priority 枚举值验证
- **安全措施**：
  - Prompt 注入检测（关键词黑名单）
  - 用户输入隔离（`<user_input>` 标签包裹）

#### 2.2 Layer 2 - Router（路由器）
- **功能描述**：接收任务并路由到编排器
- **功能点**：
  - 接收 Task 对象
  - 初始化 trace_id 上下文
  - 路由到 TaskOrchestrator

#### 2.3 Layer 3 - Registry（注册中心）
- **功能描述**：管理 Agent 和 Skill 的注册
- **AgentRegistry**：
  - 注册/注销 Agent
  - 按 capability 查询 Agent
- **SkillRegistry**：
  - 注册/查询 Skill
  - `skills/` 目录热加载（watchdog 监听）

#### 2.4 Layer 4 - Governance（治理层）
- **功能描述**：实现容错和治理机制
- **重试机制**：
  - 使用 tenacity 库
  - 指数退避（1s→2s→4s）
  - 最多 3 次重试
  - 仅重试可恢复错误
- **熔断器**：
  - 使用 pybreaker 库
  - 失败率 > 50%（10次窗口）触发
  - 30s 后半开状态
- **降级策略**：
  - 熔断开启时返回 fallback 结果
  - 写入 AuditLog 标记 `degraded=true`

#### 2.5 Layer 5 - Executor + Contract Net（执行器）
- **功能描述**：任务分解和 Agent 协作
- **任务分解**：
  - 调用 LLM（LiteLLM）
  - 返回 JSON 格式子任务列表
- **Contract Net 协议**：
  - 发布招标（BID_ANNOUNCEMENT）
  - 收集竞标（BID_RESPONSE）
  - 评分选 Agent（按 confidence 降序）
  - 发送分配（TASK_ASSIGNMENT）
  - 接收结果（TASK_RESULT）
- **SSE 推送**：
  - 每个阶段推送对应事件
  - 10 种事件类型

#### 2.6 Layer 6 - Memory（记忆层）
- **功能描述**：管理短期和长期记忆
- **短期记忆**：
  - 对话历史
  - 内存存储（dict，按 task_id 索引）
- **长期记忆**：
  - 任务结果写入 MemoryEntry 表
- **审计日志**：
  - 每个关键操作写 AuditLog
  - 包含 action、resource、user_id、trace_id、status

### 3. SSE 流式输出

#### 3.1 API 端点
- **功能描述**：提供实时事件流
- **端点**：`GET /api/v1/tasks/{task_id}/stream`
- **响应类型**：`StreamingResponse`（text/event-stream）

#### 3.2 事件类型（10 种）
1. `task_started`：任务开始
2. `sub_task_created`：子任务创建
3. `bid_received`：收到竞标
4. `agent_selected`：Agent 选中
5. `message`：消息事件
6. `skill_called`：Skill 调用
7. `skill_result`：Skill 结果
8. `sub_task_completed`：子任务完成
9. `task_completed`：任务完成
10. `task_failed`：任务失败

### 4. LLM Provider 抽象层

#### 4.1 LiteLLM 适配器
- **功能描述**：统一 LLM 调用接口
- **支持模型**：OpenAI、Anthropic 等
- **统一接口**：`generate(prompt, model, **kwargs)`

#### 4.2 模型路由
- **功能描述**：按任务类型选择模型
- **任务类型**：
  - `code`：代码生成
  - `review`：代码审查
  - `research`：研究分析
- **Fallback**：主模型失败自动切备用模型

#### 4.3 Cost 追踪
- **功能描述**：追踪 LLM 调用成本
- **记录内容**：
  - tokens_used
  - cost_usd
  - 写入 TaskExecution 表

### 5. Agent 基类和内置 Agent

#### 5.1 Agent 基类
- **功能描述**：定义 Agent 标准接口
- **核心方法**：
  - `bid(announcement) → BidResponse`：评估能力匹配度
  - `execute(assignment) → TaskResult`：执行任务
  - `report(result)`：上报结果

#### 5.2 内置 Agent
- **CoderAgent**：capabilities=["code_generation"]
- **ReviewerAgent**：capabilities=["code_review"]
- **ResearcherAgent**：capabilities=["research"]

## 非功能需求

### 1. 性能要求
- 任务分解响应时间 < 5s
- SSE 事件推送延迟 < 100ms
- RabbitMQ 消息吞吐量 > 1000 msg/s

### 2. 可靠性要求
- 重试机制保证任务最终成功（可恢复错误）
- 熔断器防止级联故障
- 死信队列保证消息不丢失

### 3. 可扩展性要求
- Agent 可动态注册和注销
- Skill 可热加载
- 模型路由可配置

### 4. 安全要求
- Prompt 注入防护
- 用户输入隔离
- 完整的审计日志

### 5. 可维护性要求
- 六层架构清晰分层
- 完善的单元测试
- 遵循项目编码规范

## 数据模型

### MemoryEntry
- `id`：记忆 ID
- `task_id`：任务 ID
- `content`：记忆内容
- `type`：记忆类型
- `created_at`：创建时间

### AuditLog
- `id`：日志 ID
- `action`：操作类型
- `resource`：资源类型
- `user_id`：用户 ID
- `trace_id`：追踪 ID
- `status`：状态
- `degraded`：是否降级
- `created_at`：创建时间

### TaskExecution
- `id`：执行 ID
- `task_id`：任务 ID
- `agent_id`：Agent ID
- `tokens_used`：使用的 token 数
- `cost_usd`：成本（美元）
- `feedback`：反馈
- `created_at`：创建时间

## API 端点

### SSE 流式输出
- `GET /api/v1/tasks/{task_id}/stream` - 实时事件流

### 内部消息
- RabbitMQ 消息总线（内部通信）

## 验收标准

1. 创建任务后 Executor 能自动拆解成子任务
2. 子任务通过 RabbitMQ 广播招标
3. Orchestrator 能评分选出最佳 Agent
4. Agent 执行完毕后结果能回传并合并
5. SSE 能实时推送 10 种事件
6. Agent 执行失败时触发重试（最多 3 次）
7. 熔断器开启后请求快速失败
8. AuditLog 表中有完整执行记录
9. 所有测试通过
10. 性能指标满足要求