# 多智能体协同框架 - 架构设计 (ARCHITECTURE.md)

## 1. 核心设计理念

**Harness Engineering**：Agent = Model + Harness
- Model 提供"思考"能力
- Harness 负责"让它真的能干活的工程支撑"

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI API Layer                        │
│         /tasks  /agents  /skills  /auth  /exports  /stream      │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    Task Orchestrator (第5层)                     │
│   任务分解(LLM) → Agent协商 → Skill调用 → 结果合并               │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    Message Bus (消息总线)                        │
│   Pub/Sub 广播 + Request/Response 点对点 + SSE 流式输出         │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                   Agent Coordinator (协商器)                     │
│   Contract Net 协议：发布 → 竞标 → 评分 → 签约 → 评估           │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                     Governance (容错治理)                        │
│   指数退避重试(tenacity) + 熔断(pybreaker) + 降级                │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                  Registry (注册中心)                             │
│   AgentRegistry + SkillRegistry + ToolRouter                    │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                  Validator (输入校验)                             │
│   Pydantic Schema + Prompt注入检测 + 长度/类型约束              │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│               Memory (记忆状态/审计日志)                         │
│   短期记忆(对话历史) + 长期记忆(任务结果) + trace_id追踪         │
└─────────────────────────────────────────────────────────────────┘
```

## 3. 核心模块

### 3.1 消息总线 (MessageBus)
- **PubSubChannel**：Agent 间广播消息（如招标公告）
- **DirectChannel**：点对点 request/response
- **SSEStreamer**：流式输出到前端
- 消息格式：`{type, from, to, payload, timestamp, correlation_id}`

### 3.2 注册中心 (Registry)
- **AgentRegistry**：注册/查询 Agent 元数据（id、capabilities、model、status）
- **SkillRegistry**：注册 Skill 元数据（manifest、entry_point、schema）
- **热加载**：本地 skills/ 目录变更自动刷新

### 3.3 路由分发 (Router)
- **AgentRouter**：根据子任务能力需求路由到最佳 Agent
- **SkillRouter**：根据 Skill ID 路由到具体执行模块

### 3.4 容错治理 (Governance)
- **重试**：指数退避重试（tenacity），最多 3 次
- **熔断**：连续失败触发熔断（pybreaker）
- **降级**：返回友好降级文案
- **分类**：业务异常不重试，系统异常重试

### 3.5 执行编排 (Executor)
- **TaskOrchestrator**：任务分解 → Agent 协商 → Skill 调用 → 结果合并
- **AgentCoordinator**：Contract Net 协议变种（竞标 + 评分 + 签约）

### 3.6 输入校验 (Validator)
- **Pydantic Schema**：强类型校验
- **必填字段检测**
- **Prompt 注入关键词检测**
- **长度/类型约束**

### 3.7 记忆状态 (Memory)
- **短期记忆**：Agent 间对话历史（协商上下文）
- **长期记忆**：任务结果持久化（后续任务参考）
- **审计日志**：全链路 trace_id

### 3.8 LLM Provider 抽象层 (LLM)
- **Provider 接口**：统一 LLM 调用接口
- **LiteLLM 适配**：通过 LiteLLM 统一多厂商 API
- **模型选择**：简单任务用便宜模型，复杂任务用贵模型
- **Fallback 策略**：主模型失败自动切换到备选模型
- **Cost 追踪**：每次调用记录 token 消耗和成本

### 3.9 数据导出 (Exporter)
- **数据收集**：自动收集用户输入、Agent 选择、Skill 调用、结果、用户反馈
- **数据脱敏**：导出前自动脱敏 PII 信息
- **导出格式**：JSONL（每行一条完整记录）
- **导出用途**：Agent 路由优化、Skill 模板优化、模型选择优化

## 4. 项目结构

```
src/
├── agent_forge/
│   ├── harness/           # Harness 六层实现
│   │   ├── validator.py   # 第1层 输入校验
│   │   ├── router.py      # 第2层 路由分发
│   │   ├── registry.py    # 第3层 注册中心
│   │   ├── governance.py  # 第4层 容错治理
│   │   └── executor.py    # 第5层 执行编排
│   ├── bus/               # 消息总线
│   │   ├── publisher.py   # Pub/Sub 广播 + SSE 流式输出
│   │   └── consumer.py    # 点对点通信（Request/Response）
│   ├── agents/            # Agent 实现
│   │   ├── base.py        # Agent 基类 + CodeAgent + AnalysisAgent + SearchAgent
│   │   └── coder.py       # 沙箱新增 CoderAgent
│   ├── skills/            # Skill 插件系统
│   │   ├── manager.py     # Skill 管理器
│   │   ├── loader.py      # 加载器
│   │   ├── registry.py    # 注册中心
│   │   ├── dispatcher.py  # 调度器
│   │   ├── engine.py      # 执行引擎
│   │   ├── builtin.py     # 内置 Skill 注册
│   │   ├── code_executor.py   # 代码执行 Skill
│   │   ├── installer.py       # 安装 Skill
│   │   ├── manifest.py        # 清单管理
│   │   ├── http_request.py    # HTTP 请求 Skill
│   │   ├── web_search.py      # 网页搜索 Skill
│   │   ├── weather.py         # 天气 Skill
│   │   └── update_profile.py  # 个人信息 Skill
│   ├── memory/            # 4 层记忆系统
│   ├── llm/               # LLM Provider 抽象
│   │   ├── litellm_adapter.py  # LiteLLM 适配
│   │   ├── router.py       # 模型路由
│   │   └── cost.py         # Cost 追踪
│   ├── exporter/          # 数据导出
│   ├── sandbox/           # 沙箱执行层（SandboxProviderFactory, SandboxPool, SandboxReclaimer）
│   ├── models/            # SQLAlchemy 数据模型
├── api/                   # FastAPI 路由
│   ├── main.py
│   └── routes/
│       ├── agents.py      # Agent 管理
│       ├── auth.py        # 认证
│       ├── dashboard.py   # 仪表盘
│       ├── health.py      # 健康检查
│       ├── llm.py         # LLM 配置
│       ├── memory.py      # 记忆 CRUD
│       ├── sandboxes.py   # 沙箱管理
│       ├── sessions.py    # 会话管理
│       ├── skills.py      # Skill 管理
│       ├── tasks.py       # 任务管理
│       ├── tools.py       # 工具
│       └── uploads.py     # 文件上传
└── middleware/            # 中间件
    ├── auth.py
    └── rate_limit.py
```

## 5. 执行流程

```
用户请求 (POST /api/v1/tasks)
    │
    ▼
API Layer (FastAPI)
    │
    ▼
第1层 输入校验 (Validator)
    │── Pydantic Schema 校验
    │── Prompt 注入检测
    │── 长度/类型约束
    ▼
第2层 路由分发 (Router)
    │── 任务路由到 TaskOrchestrator
    ▼
第3层 注册中心 (Registry)
    │── 查询可用 Agent 和 Skill
    ▼
第5层 执行编排 (Executor) ← 注意：实际执行在前，容错在后
    │── LLM 任务分解 → 子任务
    │── Agent 协商 (Contract Net)
    │── Skill 调用
    │── 结果合并
    ▼
第4层 容错治理 (Governance)
    │── 指数退避重试
    │── 熔断器
    │── 降级策略
    ▼
第6层 记忆状态 (Memory)
    │── 对话历史持久化
    │── 审计日志
    │── 数据收集（用于导出）
    ▼
结果返回给用户 (SSE 流式输出)
```

## 6. Agent 协商流程

```
1. TaskOrchestrator 接收任务
2. LLM 分解为子任务
3. 发布招标公告到 MessageBus（PubSub）
4. 具备能力的 Agent 提交 bid
5. Coordinator 综合评分选择最佳 Agent
6. 签约 → 执行 → 报告结果
7. 失败时重试或降级
```

## 7. Skill 插件系统

### 7.1 加载方式
- **本地热加载**：`skills/` 目录变更自动刷新
- **远程安装**：`pip install` 从 PyPI/仓库安装

### 7.2 包结构

```
my-skill/
├── pyproject.toml      # Python 包元信息 + dependencies
├── skill.md            # 指令文件（Claude Code 风格，给 LLM 的上下文和行为规范）
├── my_skill/
│   ├── __init__.py
│   └── executor.py     # 执行逻辑（给程序调用的）
└── README.md           # 使用说明
```

### 7.3 skill.md 示例（Claude Code 风格）

```markdown
<!-- @skill(name: code-review, version: 1.0.0) -->

# code-review

## 职责
审查代码质量和风格，发现潜在问题。

## 输入
- `code`: 源代码字符串

## 输出格式
1. 总体评分: [1-5]
2. 问题列表:
   - [severity] 问题描述
3. 改进建议

## 行为规范
- 关注：代码风格、安全漏洞、性能、可维护性
- 每条建议必须附带具体代码行号
```

### 7.4 executor.py 示例

```python
# my_skill/executor.py
async def execute(code: str) -> dict:
    """Skill 执行逻辑"""
    # 调用 LLM 执行审查
    result = await llm_provider.chat(messages=[...])
    return {"score": 4, "issues": [...]}
```

### 7.5 Skill 工作原理

1. `skill.md` 定义指令和行为规范（LLM 可读）
2. `executor.py` 定义程序化执行逻辑
3. `pyproject.toml` 声明依赖和 entry_point
4. 安装时同时注册 skill.md 到 SkillRegistry 和 executor 到调用器

### 7.6 内置 Skill 列表

| Skill | 文件 | 说明 |
|-------|------|------|
| code_executor | `skills/code_executor.py` | 沙箱代码执行（Docker/CubeSandbox） |
| builtin | `skills/builtin.py` | 内置 Skill 注册表 |
| http_request | `skills/http_request.py` | HTTP 请求 |
| web_search | `skills/web_search.py` | 网页搜索 |
| weather | `skills/weather.py` | 天气查询 |
| installer | `skills/installer.py` | Skill 安装 |
| update_profile | `skills/update_profile.py` | 个人信息更新 |

## 8. 沙箱执行层

### 8.1 架构

```
SandboxProviderFactory ──┬── DockerSandboxExecutor
                         ├── CubeSandboxE2BExecutor
                         ├── CubeSandboxAPIExecutor
                         └── MockSandboxExecutor
```

### 8.2 核心组件

- **SandboxProviderFactory**：工厂模式，根据配置动态创建不同 Provider
- **SandboxManager**：沙箱管理器，维护当前活跃沙箱
- **SandboxPool**：预置热沙箱池，降低冷启动延迟
- **SandboxReclaimer**：周期性回收过期/闲置沙箱

### 8.3 Sandbox API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/sandboxes` | 创建沙箱 |
| POST | `/api/v1/sandboxes/{id}/execute` | 执行代码 |
| POST | `/api/v1/sandboxes/{id}/files/read` | 读取文件 |
| POST | `/api/v1/sandboxes/{id}/files/write` | 写入文件 |
| POST | `/api/v1/sandboxes/{id}/pause` | 暂停沙箱 |
| POST | `/api/v1/sandboxes/{id}/resume` | 恢复沙箱 |
| POST | `/api/v1/sandboxes/{id}/destroy` | 销毁沙箱 |
| GET | `/api/v1/sandboxes` | 列出活跃沙箱 |

## 9. 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 后端 | FastAPI (async) | 高性能异步 API |
| LLM 网关 | LiteLLM | 统一 API + cost 追踪 |
| 消息队列 | RabbitMQ | 持久化 + ACK + 死信队列 |
| 数据库 | PostgreSQL | 开发/生产统一使用 |
| 认证 | JWT + API Key | 用户/服务间认证 |
| 重试 | tenacity | 指数退避 |
| 熔断 | pybreaker | 连续失败熔断 |
| 限流 | slowapi | Token Bucket |
