# RabbitMQ 消息队列设计 (RABBITMQ.md)

## 1. 设计目标

RabbitMQ 在本框架中承担 **Agent 协商总线** 职责，负责：

1. TaskOrchestrator → 所有 Agent 的**招标公告广播**（Pub/Sub）
2. Agent → TaskOrchestrator 的**竞标响应**（点对点）
3. TaskOrchestrator → 选中 Agent 的**任务分配**（点对点）
4. Agent → TaskOrchestrator 的**执行结果上报**（点对点）

---

## 2. 拓扑设计

### 2.1 Exchange 清单

| Exchange 名称 | 类型 | 说明 |
|--------------|------|------|
| `task.broadcast` | `fanout` | 招标公告广播，所有 Agent 都能收到 |
| `task.direct` | `direct` | 点对点消息（竞标、任务分配、结果上报） |
| `task.dlx` | `direct` | 死信 Exchange（处理失败/超时消息） |

### 2.2 Queue 清单

| Queue 名称 | 绑定 Exchange | Routing Key | 消费者 | 说明 |
|-----------|-------------|-------------|-------|------|
| `agent.{agent_id}.inbox` | `task.broadcast` + `task.direct` | `agent.{agent_id}` | 对应 Agent | 每个 Agent 独立队列，接收广播和点对点消息 |
| `orchestrator.inbox` | `task.direct` | `orchestrator` | TaskOrchestrator | 接收竞标、执行结果 |
| `task.dlq` | `task.dlx` | `dead` | 告警处理器 | 死信队列，处理失败消息 |

### 2.3 拓扑图

```
                     ┌─────────────────┐
                     │ TaskOrchestrator │
                     └────────┬────────┘
                              │ 发布招标公告
                              ▼
                    ┌──────────────────┐
                    │ task.broadcast   │  (fanout Exchange)
                    └──────────────────┘
                    /         |         \
           ────────           │           ────────
          /                   │                   \
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│agent.001.inbox  │  │agent.002.inbox  │  │agent.003.inbox  │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │ 竞标               │ 竞标               │ 竞标
         └──────────────┬─────┘                    │
                        ▼                          │
              ┌──────────────────┐                 │
              │  task.direct     │  ◄──────────────┘
              │ (direct Exchange)│
              └────────┬─────────┘
                       │ routing_key=orchestrator
                       ▼
              ┌──────────────────┐
              │orchestrator.inbox│  ← TaskOrchestrator 消费竞标/结果
              └──────────────────┘
```

---

## 3. 消息格式规范

所有消息为 JSON，包含统一的 envelope 结构：

```json
{
  "msg_id": "msg-uuid-001",
  "type": "BID_ANNOUNCEMENT | BID_RESPONSE | TASK_ASSIGNMENT | TASK_RESULT",
  "trace_id": "trace-001",
  "from": "orchestrator | agent-001",
  "to": "broadcast | agent-001 | orchestrator",
  "timestamp": "2026-06-17T10:00:00Z",
  "payload": { ... }
}
```

### 3.1 招标公告 (BID_ANNOUNCEMENT)

TaskOrchestrator → `task.broadcast` Exchange（fanout）

```json
{
  "msg_id": "msg-001",
  "type": "BID_ANNOUNCEMENT",
  "trace_id": "trace-001",
  "from": "orchestrator",
  "to": "broadcast",
  "timestamp": "2026-06-17T10:00:00Z",
  "payload": {
    "task_id": "task-001",
    "sub_task_id": "sub-001",
    "description": "review Python code style",
    "required_capabilities": ["code_review"],
    "deadline_ms": 5000,
    "priority": "high"
  }
}
```

### 3.2 竞标响应 (BID_RESPONSE)

Agent → `task.direct` Exchange（routing key: `orchestrator`）

```json
{
  "msg_id": "msg-002",
  "type": "BID_RESPONSE",
  "trace_id": "trace-001",
  "from": "agent-001",
  "to": "orchestrator",
  "timestamp": "2026-06-17T10:00:01Z",
  "payload": {
    "task_id": "task-001",
    "sub_task_id": "sub-001",
    "agent_id": "agent-001",
    "confidence": 0.92,
    "estimated_duration_ms": 3000,
    "model": "gpt-4"
  }
}
```

### 3.3 任务分配 (TASK_ASSIGNMENT)

TaskOrchestrator → `task.direct` Exchange（routing key: `agent.{agent_id}`）

```json
{
  "msg_id": "msg-003",
  "type": "TASK_ASSIGNMENT",
  "trace_id": "trace-001",
  "from": "orchestrator",
  "to": "agent-001",
  "timestamp": "2026-06-17T10:00:02Z",
  "payload": {
    "task_id": "task-001",
    "sub_task_id": "sub-001",
    "description": "review Python code style",
    "context": { "code": "def hello(): pass" },
    "skills_available": ["code-review"],
    "timeout_ms": 30000
  }
}
```

### 3.4 执行结果 (TASK_RESULT)

Agent → `task.direct` Exchange（routing key: `orchestrator`）

```json
{
  "msg_id": "msg-004",
  "type": "TASK_RESULT",
  "trace_id": "trace-001",
  "from": "agent-001",
  "to": "orchestrator",
  "timestamp": "2026-06-17T10:00:05Z",
  "payload": {
    "task_id": "task-001",
    "sub_task_id": "sub-001",
    "agent_id": "agent-001",
    "status": "success",
    "result": "代码风格符合规范，建议添加类型注解",
    "tokens_used": { "prompt": 800, "completion": 200 },
    "cost_usd": 0.015,
    "duration_ms": 2800
  }
}
```

---

## 4. Queue 配置（带 TTL 和死信）

```python
# 初始化 Queue 的声明参数
QUEUE_ARGS = {
    "orchestrator.inbox": {
        "durable": True,
        "arguments": {
            "x-message-ttl": 60_000,         # 消息 60s 未消费 → 死信
            "x-dead-letter-exchange": "task.dlx",
            "x-dead-letter-routing-key": "dead",
            "x-max-length": 10_000,           # 最多积压 10000 条
        }
    },
    "agent.{agent_id}.inbox": {
        "durable": True,
        "arguments": {
            "x-message-ttl": 30_000,         # Agent inbox 30s TTL
            "x-dead-letter-exchange": "task.dlx",
            "x-dead-letter-routing-key": "dead",
            "x-max-length": 1_000,
        }
    },
    "task.dlq": {
        "durable": True,
        "arguments": {}   # 死信队列不再设置 TTL，人工处理
    }
}
```

---

## 5. 消费者设计

### 5.1 TaskOrchestrator 消费者

- 监听 `orchestrator.inbox`
- 消息类型路由：
  - `BID_RESPONSE` → 收集竞标，等待 deadline_ms → 评分选择
  - `TASK_RESULT` → 合并子任务结果 → 推进任务状态

```python
async def consume_orchestrator_inbox():
    async with aio_pika.connect_robust(RABBITMQ_URL) as conn:
        channel = await conn.channel()
        await channel.set_qos(prefetch_count=10)
        queue = await channel.declare_queue("orchestrator.inbox", durable=True)
        async with queue.iterator() as msgs:
            async for msg in msgs:
                async with msg.process():
                    envelope = json.loads(msg.body)
                    await route_message(envelope)
```

### 5.2 Agent 消费者

- 启动时声明并绑定 `agent.{self.id}.inbox`
- 绑定到 `task.broadcast`（fanout，自动接收招标公告）
- 绑定到 `task.direct`（routing key: `agent.{self.id}`，接收任务分配）

```python
async def start_agent(agent_id: str):
    conn = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await conn.channel()
    await channel.set_qos(prefetch_count=1)   # Agent 一次只处理一个任务

    inbox = await channel.declare_queue(f"agent.{agent_id}.inbox", durable=True, arguments={...})

    # 绑定 fanout Exchange（招标公告）
    broadcast_ex = await channel.declare_exchange("task.broadcast", aio_pika.ExchangeType.FANOUT)
    await inbox.bind(broadcast_ex)

    # 绑定 direct Exchange（任务分配）
    direct_ex = await channel.declare_exchange("task.direct", aio_pika.ExchangeType.DIRECT)
    await inbox.bind(direct_ex, routing_key=f"agent.{agent_id}")

    async with inbox.iterator() as msgs:
        async for msg in msgs:
            async with msg.process(requeue=True):   # 失败时重新入队
                await handle_message(json.loads(msg.body))
```

---

## 6. 重试与死信处理

### 6.1 失败场景

| 场景 | 处理方式 |
|------|---------|
| Agent 执行失败（业务异常） | 发送 `TASK_RESULT{status: failed}`，由 Orchestrator 决定是否重试其他 Agent |
| Agent 执行超时（> timeout_ms） | 消息 TTL 触发，进入 DLQ，Orchestrator 通过超时检测发现后降级 |
| RabbitMQ 连接断开 | `aio_pika.connect_robust` 自动重连 |
| 消费者 Crash | `basic.nack` 触发重新入队，最多重试 3 次后进 DLQ |

### 6.2 DLQ 处理

```python
# 死信队列消费者：告警 + 记录
async def consume_dlq():
    async with queue.iterator() as msgs:
        async for msg in msgs:
            async with msg.process():
                envelope = json.loads(msg.body)
                logger.error("DLQ message", extra={
                    "trace_id": envelope.get("trace_id"),
                    "msg_type": envelope.get("type"),
                    "from": envelope.get("from"),
                    "reason": msg.headers.get("x-death", [{}])[0].get("reason")
                })
                # 可扩展：写入 TaskExecution 表记录失败、触发告警
```

---

## 7. RabbitMQ 本地管理

- 管理界面：`http://localhost:15672`（用户名/密码：`agent` / `agent_dev_pass`）
- 查看 Exchange：Management → Exchanges
- 查看 Queue 积压：Management → Queues
- 手动清空 DLQ：Management → Queues → task.dlq → Purge

---

## 8. 初始化脚本

后端启动时自动执行 Exchange/Queue 声明（幂等，多次执行安全）：

```python
# agentforge/bus/init.py
async def init_rabbitmq():
    conn = await aio_pika.connect_robust(RABBITMQ_URL)
    ch   = await conn.channel()

    # 声明 Exchange
    await ch.declare_exchange("task.broadcast", aio_pika.ExchangeType.FANOUT, durable=True)
    await ch.declare_exchange("task.direct",    aio_pika.ExchangeType.DIRECT, durable=True)
    await ch.declare_exchange("task.dlx",       aio_pika.ExchangeType.DIRECT, durable=True)

    # 声明 DLQ
    dlq = await ch.declare_queue("task.dlq", durable=True)
    dlx = await ch.get_exchange("task.dlx")
    await dlq.bind(dlx, routing_key="dead")

    # 声明 Orchestrator inbox
    orch_q = await ch.declare_queue("orchestrator.inbox", durable=True, arguments={
        "x-message-ttl": 60_000,
        "x-dead-letter-exchange": "task.dlx",
        "x-dead-letter-routing-key": "dead",
        "x-max-length": 10_000,
    })
    direct_ex = await ch.get_exchange("task.direct")
    await orch_q.bind(direct_ex, routing_key="orchestrator")

    await conn.close()
    logger.info("RabbitMQ topology initialized")
```
