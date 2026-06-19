# TASK-003：Harness 核心 + RabbitMQ + SSE

## 关联需求

| 用户故事 | 描述 |
|---------|------|
| US-1 | 作为全栈开发者，我想输入一个自然语言需求，让系统自动拆解任务并分派给合适的 Agent |
| US-2 | 作为全栈开发者，我想让 Agent 自动完成产品设计、UI 设计、任务拆解，减少重复性工作 |
| US-5 | 作为全栈开发者，我想看到安全的 API 调用记录，以便审计和合规 |

## 优先级

**P2** — 依赖 TASK-001 + TASK-002，是框架的核心价值所在

## 验收标准

- [ ] 创建一个任务后，Executor 能通过 LLM 自动拆解成子任务
- [ ] 子任务通过 RabbitMQ fanout 广播招标，多个 Agent 能收到并竞标
- [ ] Orchestrator 能评分选出最佳 Agent 并发送任务分配
- [ ] Agent 执行完毕后结果能回传并合并
- [ ] `GET /tasks/{id}/stream` 能实时推送 10 种 SSE 事件
- [ ] Agent 执行失败时触发重试（最多 3 次指数退避）
- [ ] 熔断器开启后请求快速失败，不阻塞后续任务
- [ ] AuditLog 表中有完整的执行记录（含 trace_id）

## 技术子项

### RabbitMQ 初始化（`src/agent_forge/bus/init.py`）

- [ ] 声明 Exchange：task.broadcast（fanout）、task.direct（direct）、task.dlx（direct）
- [ ] 声明 Queue：orchestrator.inbox（TTL 60s + 死信）、task.dlq
- [ ] 绑定 orchestrator.inbox 到 task.direct（routing_key=orchestrator）
- [ ] 启动时自动执行（幂等，多次运行安全）
- [ ] 参考：`docs/tech-design/RABBITMQ.md`

### Harness Layer 1-2：Validator + Router（`src/agent_forge/harness/`）

- [ ] **Validator**
  - Pydantic Schema 二次校验（任务描述长度、priority 枚举）
  - Prompt 注入检测：关键词黑名单（`system:`、`ignore previous`、`<|endoftext|>` 等）
  - 用户输入隔离：`<user_input>...</user_input>` 包裹

- [ ] **Router**
  - 接收 Task，初始化 trace_id 上下文
  - 路由到 TaskOrchestrator

### Harness Layer 3：Registry（`src/agent_forge/harness/registry.py`）

- [ ] AgentRegistry：注册/注销/按 capability 查询 Agent
- [ ] SkillRegistry：注册/查询 Skill
- [ ] `skills/` 目录热加载（watchdog 文件监听，变更自动刷新）

### Harness Layer 4：Governance（`src/agent_forge/harness/governance.py`）

- [ ] **重试**：tenacity，指数退避（1s→2s→4s），最多 3 次，仅重试可恢复错误
- [ ] **熔断器**：pybreaker，失败率 > 50%（10次窗口）触发，30s 后半开
- [ ] **降级**：熔断开启时返回 fallback 结果，写入 AuditLog 标记 `degraded=true`

### Harness Layer 5：Executor + Contract Net（`src/agent_forge/harness/executor.py`）

- [ ] **任务分解**：调用 LLM（LiteLLM），prompt 要求返回 JSON 格式子任务列表
- [ ] **发布招标**：向 task.broadcast Exchange 发布 `BID_ANNOUNCEMENT` 消息
- [ ] **收集竞标**：监听 orchestrator.inbox，等待 `deadline_ms`（默认 5000ms）
- [ ] **评分选 Agent**：按 confidence 降序选最高分，能力匹配度加权
- [ ] **发送分配**：向 task.direct Exchange 发送 `TASK_ASSIGNMENT`（routing_key: agent.{id}）
- [ ] **接收结果**：监听 `TASK_RESULT`，合并所有子任务结果
- [ ] **SSE 推送**：每个阶段向 SSE AsyncGenerator 推送对应事件
- [ ] 参考：`docs/tech-design/RABBITMQ.md` 第 3 节

### Harness Layer 6：Memory（`src/agent_forge/harness/memory.py`）

- [ ] **短期记忆**：对话历史，内存存储（dict，按 task_id 索引）
- [ ] **长期记忆**：任务结果写入 MemoryEntry 表（PostgreSQL）
- [ ] **审计日志**：每个关键操作写 AuditLog（action、resource、user_id、trace_id、status）

### SSE 流式输出（`src/api/routes/tasks.py` 补充）

- [ ] `GET /api/v1/tasks/{task_id}/stream`
- [ ] `StreamingResponse`（media_type=`text/event-stream`）
- [ ] 推送 10 种事件：task_started、sub_task_created、bid_received、agent_selected、message、skill_called、skill_result、sub_task_completed、task_completed、task_failed
- [ ] 参考：`docs/tech-design/API-SPEC.md` 第 8 节

### LLM Provider 抽象层（`src/agent_forge/llm/`）

- [ ] LiteLLM 适配器（`litellm_adapter.py`）：统一 OpenAI + Anthropic 调用接口
- [ ] 模型路由（`router.py`）：按任务类型（code/review/research）选模型
- [ ] Fallback：主模型失败自动切备用模型
- [ ] Cost 追踪：每次调用写入 TaskExecution.tokens_used + cost_usd
- [ ] 参考：`docs/tech-design/LLM-CONFIG.md`

### Agent 基类 + 内置 Agent（`src/agent_forge/agents/`）

- [ ] **基类**（`base.py`）
  - `bid(announcement) → BidResponse`：评估 capability 匹配度，生成 confidence
  - `execute(assignment) → TaskResult`：调用 LLM + Skill，返回结果
  - `report(result)`：向 orchestrator 上报结果

- [ ] `CoderAgent`：capabilities=["code_generation"]
- [ ] `ReviewerAgent`：capabilities=["code_review"]
- [ ] `ResearcherAgent`：capabilities=["research"]

## 产出物

- `src/agent_forge/bus/init.py` + `publisher.py` + `consumer.py`
- `src/agent_forge/harness/validator.py`
- `src/agent_forge/harness/router.py`
- `src/agent_forge/harness/registry.py`
- `src/agent_forge/harness/governance.py`
- `src/agent_forge/harness/executor.py`
- `src/agent_forge/harness/memory.py`
- `src/agent_forge/llm/litellm_adapter.py` + `router.py`
- `src/agent_forge/agents/base.py` + `coder.py` + `reviewer.py` + `researcher.py`

## 参考文档

- `docs/tech-design/ARCHITECTURE.md`
- `docs/tech-design/RABBITMQ.md`
- `docs/tech-design/API-SPEC.md` 第 8 节
- `docs/tech-design/LLM-CONFIG.md`
- `docs/product-design/PRD-多智能体框架-20260617.md` US-1、US-2、US-5
