# TASK-003 任务清单

## 迭代目标
实现 AgentForge 的核心执行引擎（Harness），包括 RabbitMQ 消息总线、六层架构、SSE 流式输出、LLM Provider 和 Agent 基类。

## 任务清单

### 阶段 1：基础设施
- [x] 创建迭代文档（PRODUCT-REQUIREMENTS.md）（已完成）
- [x] 创建迭代文档（TASK-CHECKLIST.md）（已完成）
- [x] 创建迭代文档（TECHNICAL-DESIGN.md）（已完成）
- [x] 安装依赖包（tenacity、pybreaker、watchdog、litellm）（已完成）

### 阶段 2：RabbitMQ 消息总线
- [x] 实现 RabbitMQ 初始化（`src/agent_forge/bus/init.py`）（已完成）
  - 声明 Exchange（task.broadcast、task.direct、task.dlx）
  - 声明 Queue（orchestrator.inbox、task.dlq）
  - 绑定关系
  - 幂等性保证
- [x] 实现消息发布（`src/agent_forge/bus/publisher.py`）（已完成）
  - 发布招标消息
  - 发布任务分配
  - 发布结果消息
- [x] 实现消息消费（`src/agent_forge/bus/consumer.py`）（已完成）
  - 监听 orchestrator.inbox
  - 处理竞标响应
  - 处理任务结果

### 阶段 3：Harness Layer 1-2（Validator + Router）
- [x] 实现 Validator（`src/agent_forge/harness/validator.py`）（已完成）
  - Pydantic Schema 二次校验
  - Prompt 注入检测
  - 用户输入隔离
- [x] 实现 Router（`src/agent_forge/harness/router.py`）（已完成）
  - 接收 Task
  - 初始化 trace_id
  - 路由到 Orchestrator

### 阶段 4：Harness Layer 3（Registry）
- [x] 实现 AgentRegistry（`src/agent_forge/harness/registry.py`）（已完成）
  - 注册/注销 Agent
  - 按 capability 查询
- [x] 实现 SkillRegistry（`src/agent_forge/harness/registry.py`）（已完成）
  - 注册/查询 Skill
  - 热加载机制（watchdog）

### 阶段 5：Harness Layer 4（Governance）
- [x] 实现重试机制（`src/agent_forge/harness/governance.py`）（已完成）
  - tenacity 配置
  - 指数退避
  - 可恢复错误判断
- [x] 实现熔断器（`src/agent_forge/harness/governance.py`）（已完成）
  - pybreaker 配置
  - 失败率阈值
  - 半开状态
- [x] 实现降级策略（`src/agent_forge/harness/governance.py`）（已完成）
  - fallback 结果
  - AuditLog 标记

### 阶段 6：Harness Layer 5（Executor + Contract Net）
- [x] 实现任务分解（`src/agent_forge/harness/executor.py`）（已完成）
  - LLM 调用
  - JSON 格式子任务列表
- [x] 实现 Contract Net 协议（`src/agent_forge/harness/executor.py`）（已完成）
  - 发布招标
  - 收集竞标
  - 评分选 Agent
  - 发送分配
  - 接收结果
- [x] 实现 SSE 推送（`src/agent_forge/harness/executor.py`）（已完成）
  - 10 种事件类型
  - AsyncGenerator

### 阶段 7：Harness Layer 6（Memory）
- [x] 实现短期记忆（`src/agent_forge/harness/memory.py`）（已完成）
  - 内存存储
  - 按 task_id 索引
- [x] 实现长期记忆（`src/agent_forge/harness/memory.py`）（已完成）
  - MemoryEntry 表写入
- [x] 实现审计日志（`src/agent_forge/harness/memory.py`）（已完成）
  - AuditLog 表写入
  - 关键操作记录

### 阶段 8：SSE 流式输出 API
- [x] 实现 SSE 端点（`src/agent_forge/api/sse.py`）（已完成）
  - GET /api/v1/tasks/{task_id}/stream
  - StreamingResponse
  - 事件格式

### 阶段 9：LLM Provider 抽象层
- [x] 实现 LiteLLM 适配器（`src/agent_forge/llm/provider.py`）（已完成）
  - 统一调用接口
  - 多模型支持
- [x] 实现模型路由（`src/agent_forge/llm/provider.py`）（已完成）
  - 按任务类型选模型
  - Fallback 机制
- [x] 实现 Cost 追踪（`src/agent_forge/llm/provider.py`）（已完成）
  - tokens_used 记录
  - cost_usd 记录

### 阶段 10：Agent 基类和内置 Agent
- [x] 实现 Agent 基类（`src/agent_forge/agents/base.py`）（已完成）
  - bid 方法
  - execute 方法
  - report 方法
- [x] 实现 CodeAgent（`src/agent_forge/agents/base.py`）（已完成）
- [x] 实现 AnalysisAgent（`src/agent_forge/agents/base.py`）（已完成）
- [x] 实现 SearchAgent（`src/agent_forge/agents/base.py`）（已完成）

### 阶段 11：测试和验证
- [x] 编写 Harness 各层测试（已完成）
  - test_validator.py（8 个测试）
  - test_governance.py（5 个测试）
  - test_registry.py（8 个测试）
- [x] 验收标准检查（已完成）

### 阶段 12：文档和提交
- [x] 更新主文档索引（已完成）
- [x] Git commit 和 push（已完成）

## 技术挑战

### 挑战 1：RabbitMQ 异步消息处理
**描述**：需要在 async 上下文中处理 RabbitMQ 消息

**解决方案**：
- 使用 aio_pika 库
- 实现 async consumer 和 publisher
- 使用 asyncio.Queue 进行消息传递

### 挑战 2：Contract Net 协议实现
**描述**：需要实现完整的招标-竞标-分配流程

**解决方案**：
- 定义清晰的消息格式
- 实现超时机制（deadline_ms）
- 实现评分算法（confidence + capability 匹配度）

### 挑战 3：SSE 流式输出
**描述**：需要在 async 上下文中实现 SSE 推送

**解决方案**：
- 使用 FastAPI StreamingResponse
- 实现 AsyncGenerator
- 使用 asyncio.Queue 作为事件缓冲

### 挑战 4：熔断器和重试集成
**描述**：需要在多个层级集成容错机制

**解决方案**：
- 使用装饰器模式
- 在 Executor 层集成
- 在 LLM 调用层集成

## 验收标准检查

- [x] 创建任务后 Executor 能自动拆解成子任务
- [x] 子任务通过 RabbitMQ 广播招标
- [x] Orchestrator 能评分选出最佳 Agent
- [x] Agent 执行完毕后结果能回传并合并
- [x] SSE 能实时推送 10 种事件
- [x] Agent 执行失败时触发重试（最多 3 次）
- [x] 熔断器开启后请求快速失败
- [x] AuditLog 表中有完整执行记录
- [x] 所有测试通过（21/21）
- [x] 性能指标满足要求

## 下一步计划

1. 完成迭代文档（TECHNICAL-DESIGN.md）✅
2. 安装必要依赖 ✅
3. 开始实现 RabbitMQ 消息总线 ✅
4. 逐步实现 Harness 各层 ✅
5. 编写测试并验证 ✅
6. 更新文档并提交 ✅