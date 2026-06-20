# TASK-003 技术设计文档

## 系统架构

### 整体架构
AgentForge 采用六层 Harness 架构设计，每层职责清晰：

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                    │
├─────────────────────────────────────────────────────────┤
│                  Harness Layer 6: Memory                  │
│  (短期记忆、长期记忆、审计日志)                              │
├─────────────────────────────────────────────────────────┤
│              Harness Layer 5: Executor                    │
│  (任务分解、Contract Net、SSE 推送)                         │
├─────────────────────────────────────────────────────────┤
│            Harness Layer 4: Governance                    │
│  (重试、熔断、降级)                                         │
├─────────────────────────────────────────────────────────┤
│              Harness Layer 3: Registry                    │
│  (AgentRegistry、SkillRegistry、热加载)                     │
├─────────────────────────────────────────────────────────┤
│           Harness Layer 2: Router                         │
│  (任务路由、trace_id 初始化)                                │
├─────────────────────────────────────────────────────────┤
│           Harness Layer 1: Validator                      │
│  (输入验证、Prompt 注入防护)                                │
├─────────────────────────────────────────────────────────┤
│              RabbitMQ Message Bus                         │
│  (消息队列、Contract Net 协议)                              │
├─────────────────────────────────────────────────────────┤
│              LLM Provider Layer                           │
│  (LiteLLM、模型路由、Cost 追踪)                              │
├─────────────────────────────────────────────────────────┤
│                  Agent Layer                              │
│  (基类、内置 Agent)                                         │
└─────────────────────────────────────────────────────────┘
```

### 技术栈
- **消息队列**：RabbitMQ + aio_pika
- **容错机制**：tenacity（重试）、pybreaker（熔断）
- **文件监听**：watchdog（热加载）
- **LLM 调用**：LiteLLM
- **流式输出**：FastAPI StreamingResponse + SSE
- **异步编程**：asyncio + AsyncGenerator

## RabbitMQ 消息总线设计

### Exchange 和 Queue 拓扑

```
┌──────────────────┐
│  task.broadcast  │ (fanout)
│  招标广播        │
└──────────────────┘
         │
         ├──────────────┐
         │              │
         ▼              ▼
┌─────────────┐  ┌─────────────┐
│ Agent 1     │  │ Agent 2     │
│ 竞标队列    │  │ 竞标队列    │
└─────────────┘  └─────────────┘

┌──────────────────┐
│   task.direct    │ (direct)
│   定向传递       │
└──────────────────┘
         │
         ├─ routing_key: orchestrator
         │
         ▼
┌──────────────────┐
│ orchestrator.inbox│
│ TTL: 60s         │
│ 死信: task.dlx   │
└──────────────────┘

┌──────────────────┐
│    task.dlx      │ (direct)
│    死信交换器    │
└──────────────────┘
         │
         ▼
┌──────────────────┐
│    task.dlq      │
│    死信队列      │
└──────────────────┘
```

### 消息格式

#### BID_ANNOUNCEMENT（招标公告）
```json
{
  "message_type": "BID_ANNOUNCEMENT",
  "task_id": "task-uuid",
  "sub_task_id": "subtask-uuid",
  "description": "子任务描述",
  "required_capabilities": ["code_generation"],
  "deadline_ms": 5000,
  "trace_id": "trace-uuid",
  "timestamp": "2025-06-20T00:00:00Z"
}
```

#### BID_RESPONSE（竞标响应）
```json
{
  "message_type": "BID_RESPONSE",
  "task_id": "task-uuid",
  "sub_task_id": "subtask-uuid",
  "agent_id": "agent-uuid",
  "confidence": 0.85,
  "estimated_time_ms": 30000,
  "trace_id": "trace-uuid",
  "timestamp": "2025-06-20T00:00:00Z"
}
```

#### TASK_ASSIGNMENT（任务分配）
```json
{
  "message_type": "TASK_ASSIGNMENT",
  "task_id": "task-uuid",
  "sub_task_id": "subtask-uuid",
  "agent_id": "agent-uuid",
  "description": "子任务描述",
  "context": {...},
  "trace_id": "trace-uuid",
  "timestamp": "2025-06-20T00:00:00Z"
}
```

#### TASK_RESULT（任务结果）
```json
{
  "message_type": "TASK_RESULT",
  "task_id": "task-uuid",
  "sub_task_id": "subtask-uuid",
  "agent_id": "agent-uuid",
  "status": "completed",
  "result": "执行结果",
  "tokens_used": 1000,
  "cost_usd": 0.02,
  "trace_id": "trace-uuid",
  "timestamp": "2025-06-20T00:00:00Z"
}
```

## Harness 各层设计

### Layer 1: Validator

#### 输入验证
```python
class Validator:
    def validate_task(self, task: TaskCreateRequest) -> ValidationResult:
        # 1. Pydantic Schema 二次校验
        # 2. 描述长度限制（≤ 500 字）
        # 3. priority 枚举验证
        # 4. Prompt 注入检测
        # 5. 用户输入隔离
        pass
```

#### Prompt 注入检测关键词
```python
BLACKLIST = [
    "system:",
    "ignore previous",
    "ignore all",
    "forget everything",
    "disregard",
    "override",
    "bypass",
]
```

### Layer 2: Router

#### 任务路由
```python
class Router:
    async def route_task(self, task: Task) -> str:
        # 1. 初始化 trace_id
        # 2. 路由到 TaskOrchestrator
        # 3. 返回 trace_id
        pass
```

### Layer 3: Registry

#### AgentRegistry
```python
class AgentRegistry:
    def register(self, agent: Agent) -> None:
        pass
    
    def unregister(self, agent_id: str) -> None:
        pass
    
    def query_by_capability(self, capability: str) -> list[Agent]:
        pass
```

#### SkillRegistry（热加载）
```python
class SkillRegistry:
    def __init__(self):
        self.skills = {}
        self._watcher = Observer()
        self._watcher.schedule(
            SkillHandler(self),
            path="skills/",
            recursive=True
        )
        self._watcher.start()
    
    def register(self, skill: Skill) -> None:
        pass
    
    def query(self, skill_id: str) -> Skill:
        pass
```

### Layer 4: Governance

#### 重试机制（tenacity）
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type(RecoverableError)
)
async def execute_with_retry(self, task: Task):
    pass
```

#### 熔断器（pybreaker）
```python
from pybreaker import CircuitBreaker

breaker = CircuitBreaker(
    fail_max=5,  # 10 次窗口中 5 次失败 = 50%
    reset_timeout=30  # 30s 后半开
)

@breaker
async def execute_with_circuit_breaker(self, task: Task):
    pass
```

#### 降级策略
```python
async def execute_with_fallback(self, task: Task):
    try:
        return await self.execute_with_circuit_breaker(task)
    except CircuitBreakerError:
        # 熔断开启，返回 fallback
        result = self.get_fallback_result(task)
        await self.log_degraded_execution(task, result)
        return result
```

### Layer 5: Executor + Contract Net

#### 任务分解
```python
class Executor:
    async def decompose_task(self, task: Task) -> list[SubTask]:
        prompt = f"""
        请将以下任务分解为子任务：
        任务描述：{task.description}
        
        返回 JSON 格式：
        [
            {"description": "子任务1", "capabilities": ["code_generation"]},
            {"description": "子任务2", "capabilities": ["code_review"]}
        ]
        """
        response = await self.llm.generate(prompt, model="gpt-4")
        sub_tasks = json.loads(response)
        return sub_tasks
```

#### Contract Net 协议
```python
class Executor:
    async def run_contract_net(self, sub_task: SubTask):
        # 1. 发布招标
        announcement = BidAnnouncement(sub_task)
        await self.publisher.broadcast(announcement)
        
        # 2. 收集竞标（等待 deadline_ms）
        bids = await self.collect_bids(deadline_ms=5000)
        
        # 3. 评分选 Agent
        selected_agent = self.select_agent(bids)
        
        # 4. 发送分配
        assignment = TaskAssignment(sub_task, selected_agent)
        await self.publisher.send_assignment(assignment)
        
        # 5. 接收结果
        result = await self.receive_result(sub_task.id)
        
        # 6. SSE 推送
        await self.sse_push("agent_selected", selected_agent)
        
        return result
    
    def select_agent(self, bids: list[BidResponse]) -> Agent:
        # 评分算法：confidence * capability_match_score
        scored_bids = [
            (bid, bid.confidence * self.calc_capability_match(bid))
            for bid in bids
        ]
        # 降序排序，选最高分
        return max(scored_bids, key=lambda x: x[1])[0].agent
```

#### SSE 推送
```python
class Executor:
    async def sse_stream(self, task_id: str) -> AsyncGenerator:
        queue = asyncio.Queue()
        
        # 注册事件监听器
        self.event_bus.subscribe(task_id, queue)
        
        async def generator():
            while True:
                event = await queue.get()
                if event.type == "task_completed":
                    break
                yield f"event: {event.type}\ndata: {json.dumps(event.data)}\n\n"
        
        return generator()
```

### Layer 6: Memory

#### 短期记忆
```python
class Memory:
    def __init__(self):
        self.short_term = {}  # task_id -> list[Message]
    
    def add_message(self, task_id: str, message: Message):
        self.short_term[task_id].append(message)
    
    def get_history(self, task_id: str) -> list[Message]:
        return self.short_term.get(task_id, [])
```

#### 长期记忆
```python
class Memory:
    async def save_to_long_term(self, task_id: str, result: str):
        entry = MemoryEntry(
            task_id=task_id,
            content=result,
            type="task_result"
        )
        await self.db.add(entry)
        await self.db.commit()
```

#### 审计日志
```python
class Memory:
    async def log_audit(
        self,
        action: str,
        resource: str,
        user_id: str,
        trace_id: str,
        status: str,
        degraded: bool = False
    ):
        log = AuditLog(
            action=action,
            resource=resource,
            user_id=user_id,
            trace_id=trace_id,
            status=status,
            degraded=degraded
        )
        await self.db.add(log)
        await self.db.commit()
```

## SSE 流式输出设计

### API 端点
```python
@router.get("/api/v1/tasks/{task_id}/stream")
async def stream_task_events(
    task_id: str,
    executor: Executor = Depends(get_executor)
):
    return StreamingResponse(
        executor.sse_stream(task_id),
        media_type="text/event-stream"
    )
```

### 事件格式
```
event: task_started
data: {"task_id": "uuid", "timestamp": "..."}

event: sub_task_created
data: {"sub_task_id": "uuid", "description": "..."}

event: bid_received
data: {"agent_id": "uuid", "confidence": 0.85}

event: agent_selected
data: {"agent_id": "uuid", "score": 0.9}

event: message
data: {"content": "...", "role": "agent"}

event: skill_called
data: {"skill_id": "uuid", "input": "..."}

event: skill_result
data: {"skill_id": "uuid", "output": "..."}

event: sub_task_completed
data: {"sub_task_id": "uuid", "result": "..."}

event: task_completed
data: {"task_id": "uuid", "result": "..."}

event: task_failed
data: {"task_id": "uuid", "error": "..."}
```

## LLM Provider 设计

### LiteLLM 适配器
```python
class LiteLLMAdapter:
    async def generate(
        self,
        prompt: str,
        model: str,
        **kwargs
    ) -> str:
        response = await litellm.acompletion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        return response.choices[0].message.content
    
    async def count_tokens(self, text: str) -> int:
        return litellm.token_counter(text=text)
    
    async def calculate_cost(self, model: str, tokens: int) -> float:
        return litellm.cost_per_token(model, tokens)
```

### 模型路由
```python
class ModelRouter:
    ROUTING = {
        "code_generation": "gpt-4",
        "code_review": "claude-3-opus",
        "research": "gpt-4-turbo",
    }
    
    FALLBACK = {
        "gpt-4": "gpt-3.5-turbo",
        "claude-3-opus": "claude-3-sonnet",
    }
    
    def select_model(self, task_type: str) -> str:
        primary = self.ROUTING.get(task_type, "gpt-4")
        return primary
    
    async def generate_with_fallback(
        self,
        prompt: str,
        task_type: str
    ) -> str:
        primary = self.select_model(task_type)
        try:
            return await self.adapter.generate(prompt, primary)
        except Exception:
            fallback = self.FALLBACK[primary]
            return await self.adapter.generate(prompt, fallback)
```

### Cost 追踪
```python
class CostTracker:
    async def track_usage(
        self,
        task_id: str,
        agent_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ):
        total_tokens = prompt_tokens + completion_tokens
        cost = await self.adapter.calculate_cost(model, total_tokens)
        
        execution = TaskExecution(
            task_id=task_id,
            agent_id=agent_id,
            tokens_used=total_tokens,
            cost_usd=cost
        )
        await self.db.add(execution)
        await self.db.commit()
```

## Agent 设计

### Agent 基类
```python
class BaseAgent:
    def __init__(self, id: str, capabilities: list[str]):
        self.id = id
        self.capabilities = capabilities
    
    async def bid(self, announcement: BidAnnouncement) -> BidResponse:
        # 评估能力匹配度
        match_score = self.calc_capability_match(
            announcement.required_capabilities
        )
        confidence = match_score * self.self_confidence
        
        return BidResponse(
            agent_id=self.id,
            confidence=confidence,
            estimated_time_ms=self.estimate_time(announcement)
        )
    
    async def execute(self, assignment: TaskAssignment) -> TaskResult:
        # 调用 LLM + Skill
        result = await self.llm.generate(
            assignment.description,
            context=assignment.context
        )
        
        return TaskResult(
            sub_task_id=assignment.sub_task_id,
            agent_id=self.id,
            status="completed",
            result=result
        )
    
    async def report(self, result: TaskResult):
        # 向 orchestrator 上报结果
        await self.publisher.send_result(result)
```

### 内置 Agent
```python
class CoderAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            id="coder-agent",
            capabilities=["code_generation"]
        )

class ReviewerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            id="reviewer-agent",
            capabilities=["code_review"]
        )

class ResearcherAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            id="researcher-agent",
            capabilities=["research"]
        )
```

## 数据库设计

### MemoryEntry 表
```sql
CREATE TABLE memory_entries (
    id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL,
    content TEXT NOT NULL,
    type VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE INDEX idx_memory_task_id ON memory_entries(task_id);
CREATE INDEX idx_memory_type ON memory_entries(type);
```

### AuditLog 表
```sql
CREATE TABLE audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    action VARCHAR(50) NOT NULL,
    resource VARCHAR(50) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    trace_id VARCHAR(36) NOT NULL,
    status VARCHAR(20) NOT NULL,
    degraded BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_audit_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_trace_id ON audit_logs(trace_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
```

### TaskExecution 表
```sql
CREATE TABLE task_executions (
    id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL,
    agent_id VARCHAR(36) NOT NULL,
    tokens_used INTEGER NOT NULL,
    cost_usd DECIMAL(10, 6) NOT NULL,
    feedback TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);

CREATE INDEX idx_execution_task_id ON task_executions(task_id);
CREATE INDEX idx_execution_agent_id ON task_executions(agent_id);
```

## 性能优化

### RabbitMQ 性能
- 使用异步 IO（aio_pika）
- 消息批量处理
- 连接池管理

### SSE 性能
- 使用 AsyncGenerator
- 事件缓冲队列
- 背压控制

### LLM 调用性能
- 模型路由优化
- Fallback 快速切换
- Cost 追踪异步写入

## 安全考虑

### Prompt 注入防护
- 关键词黑名单检测
- 用户输入隔离标签
- 输入长度限制

### 消息安全
- RabbitMQ 认证
- 消息签名验证
- trace_id 关联追踪

### 审计日志
- 所有关键操作记录
- degraded 标记
- trace_id 关联

## 测试策略

### 单元测试
- RabbitMQ 消息测试
- Harness 各层测试
- Agent 测试

### 集成测试
- Contract Net 流程测试
- SSE 流测试
- LLM 调用测试

### 性能测试
- RabbitMQ 吞吐量测试
- SSE 延迟测试
- LLM 调用延迟测试

## 部署考虑

### RabbitMQ 配置
```yaml
rabbitmq:
  host: localhost
  port: 5672
  user: agentforge
  password: ***
  vhost: /agentforge
```

### LLM 配置
```yaml
llm:
  openai_api_key: ***
  anthropic_api_key: ***
  default_model: gpt-4
  fallback_model: gpt-3.5-turbo
```

### 熔断器配置
```yaml
circuit_breaker:
  fail_max: 5
  reset_timeout: 30
```

## 未来扩展

### 计划中的功能
1. **多模型路由**：支持更多 LLM 模型
2. **Agent 学习**：Agent 自我优化
3. **Skill 市场**：Skill 共享和交易
4. **分布式执行**：多节点任务执行

### 可扩展性设计
1. **插件化架构**：Agent 和 Skill 可插拔
2. **配置化路由**：模型路由可配置
3. **水平扩展**：RabbitMQ 支持多消费者