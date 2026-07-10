# 多智能体协同框架 - 架构设计 (ARCHITECTURE.md)

## 1. 核心设计理念

**Harness Engineering**：Agent = Model + Harness
- Model 提供"思考"能力
- Harness 负责"让它真的能干活的工程支撑"

> 当前状态（TASK-037）：本文保留 Harness 六层架构作为底层工程框架说明。面向产品主链路的新开发应优先阅读 `docs/architecture/AI-RUNTIME-CONVERGENCE.md`，以 `Project -> Intent -> Pipeline -> Stage -> Agent/Profile -> Skill Runtime -> Artifact -> Delivery -> Eval Feedback` 为最新运行时事实源。

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       FastAPI API Layer                                    │
│ /projects /sessions /pipeline /agents /skills /llm /evaluation /exports /stream │
└────────────────────────┬────────────────────────────────────────────────────┘
                         │
         ┌───────────────┼──────────────────────────┐
         │               ▼                          │
┌─────────────────┐  ┌────────────────┐  ┌─────────────────┐
│ Validator       │  │  SandboxPool   │  │  SandboxManager │
│ 输入校验         │  │  (热沙箱池)     │  │  (TTL 管理)     │
│ ───────────────  │  │  ────────────  │  │  ────────────   │
│ • Pydantic      │  │  • bootstrap   │  │  • 生命周期     │
│ • Prompt注入检测 │  │  • acquire     │  │  • TTL续期      │
│ • 长度/类型约束  │  │  • release     │  │  • 降级        │
└─────────────────┘  │  • cleanup     │  │  • 降级        │
                     │  • cold-start  │  └───────┬─────────┘
                     │  • drain       │          │
                     └────────────────┘          │
            ┌────────┴────────┐                  │
            │                 ▼                  │
┌─────────────────┐  ┌────────────────┐  ┌─────────────────┐
│ SandboxReclaimer│  │ Router         │  │ Registry        │
│ TTL自动回收      │  │ 路由分发        │  │ 注册中心         │
│ ───────────────  │  │ ─────────────  │  │ ─────────────  │
│ • 后台扫描循环   │  │ • AgentRouter  │  │ • AgentRegistry │
│ • pause → destroy│  │ • SkillRouter  │  │ • SkillRegistry │
│ • pool drain    │  │ • auto模式路由 │  │ • 热加载        │
└─────────────────┘  └───────┬────────┘  └────────┬────────┘
                             │                     │
              ┌──────────────┼─────────────────────┤
              │              ▼                     │
┌─────────────────────────────────────────────────────┐
│                Governance (容错治理)                 │
│  重试(tenacity 指数退避) + 熔断(pybreaker) + 降级    │
└────────────────────────┬────────────────────────────┘
                         │
┌─────────────────────────────────────────────────────┐
│                Executor (执行编排)                   │
│  任务分解(LLM) → Agent协商(Contract Net) → Skill调用│
└────────────────────────┬────────────────────────────┘
                         │
┌─────────────────────────────────────────────────────┐
│              Message Bus (消息总线)                  │
│  Pub/Sub 广播 + Request/Response 点对点 + SSE 流式   │
└────────────────────────┬────────────────────────────┘
                         │
┌─────────────────────────────────────────────────────┐
│              LLM Provider 抽象层                     │
│  LiteLLM 统一多厂商 API + 模型路由 + Cost 追踪       │
└────────────────────────┬────────────────────────────┘
                         │
┌─────────────────────────────────────────────────────┐
│              Memory (记忆状态 / 审计)                │
│  Working / Episodic / Semantic / User 四层记忆      │
└─────────────────────────────────────────────────────┘
```

### 分层说明

| 层 | 职责 | 关键组件 |
|----|------|---------|
| **API 层** | HTTP 入口、SSE 流式输出 | FastAPI、`/tasks`、`/sandboxes` |
| **Validator** | 输入校验、安全边界 | Pydantic Schema、Prompt 注入检测 |
| **Router** | 任务路由、需求分类 | AgentRouter、SkillRouter、auto 模式 |
| **Registry** | 组件发现与热加载 | AgentRegistry、SkillRegistry |
| **Governance** | 容错、弹性 | tenacity 重试、pybreaker 熔断 |
| **Executor** | 执行编排、Agent 协商 | TaskOrchestrator、Contract Net 协议 |
| **Message Bus** | 进程间通信、SSE 推送 | Pub/Sub、Request/Response、SSE |
| **LLM 抽象** | 多厂商统一调用 | LiteLLM、模型路由、Cost 追踪 |
| **Sandbox** | 代码隔离执行 | SandboxPool（热池）+ Manager + Reclaimer |
| **Memory** | 状态持久化、审计 | 4 层记忆、trace_id 追踪 |

## 3. 核心模块

### 3.1 消息总线 (MessageBus)
- **PubSubChannel**：Agent 间广播消息（如招标公告）
- **DirectChannel**：点对点 request/response
- **SSEStreamer**：流式输出到前端
- 消息格式：`{type, from, to, payload, timestamp, correlation_id}`

### 3.2 注册中心 (Registry)
- **AgentResolver**：按用户覆盖、项目默认、阶段默认和系统默认解析 AgentProfile。
- **SkillRegistry**：注册 Skill tool_defs、executor、runtime_spec 和 tool -> skill 映射。
- **SkillInstaller**：第三方 Skill 安装前预览 Manifest、权限、风险和工具，安装后刷新 runtime registry。
- **StageSkillPolicy**：根据阶段策略、Agent allowlist 和 SkillRuntimeSpec permissions 过滤 LLM 可见工具。
- **热加载**：内置 Skill 启动注册时写入 RuntimeSpec，第三方 Skill 安装后显式刷新。

### 3.3 路由分发 (Router)
- **Pipeline Catalog**：按 intent 返回 StageDefinition，是阶段语义后端事实源。
- **AgentResolver**：根据 StageDefinition 和运行时上下文选择 AgentProfile。
- **ModelRouter**：根据请求覆盖、AgentProfile、StageDefinition 和 legacy settings 解析 ModelRoute。
- **SkillPolicy**：在 SkillExecutionEngine 前过滤当前阶段可见 tools。
- **SkillDispatcher**：根据 tool_name 路由到具体 Skill executor，并执行权限、审计和 Eval 记录。

### 3.4 容错治理 (Governance)
- **重试**：指数退避重试（tenacity），最多 3 次
- **熔断**：连续失败触发熔断（pybreaker）
- **降级**：返回友好降级文案
- **分类**：业务异常不重试，系统异常重试
- **确认策略**：`GovernancePolicy` 统一阶段确认、Delivery 写回确认和高风险 Skill 权限决策。

### 3.5 执行编排 (Executor)
- **TaskOrchestrator**：任务分解 → Agent 协商 → Skill 调用 → 结果合并
- **AgentCoordinator**：Contract Net 协议变种（竞标 + 评分 + 签约）

### 3.6 输入校验 (Validator)
- **Pydantic Schema**：强类型校验
- **必填字段检测**
- **Prompt 注入关键词检测**
- **长度/类型约束**

### 3.7 记忆状态 (Memory)

**4 层记忆架构**（详见 `docs/tech-design/DATABASE.md` 第 5 节）：

| 层 | 存储 | 说明 |
|----|------|------|
| **Working Memory** | 内存 / 会话 | 当前会话上下文，短期有效 |
| **Episodic Memory** | 数据库 | 任务执行历史、会话记录 |
| **Semantic Memory** | PostgreSQL + pgvector | 语义向量检索，支持相似记忆召回 |
| **User Memory** | 数据库 | 用户偏好、配置、Agent 设置 |

- **Manager**：记忆 CRUD 统一入口
- **Embedder**：向量化嵌入（语义记忆写入/检索）
- **Retriever**：多路召回（关键词 + 向量相似度）
- **trace_id**：全链路追踪（`tracing.py` + `middleware/trace.py`）

### 3.8 LLM Provider 抽象层 (LLM)
- **Provider 接口**：统一 LLM 调用接口（`llm/provider.py`）
- **LiteLLM 适配**：通过 LiteLLM 统一多厂商 API
- **模型选择**：简单任务用便宜模型，复杂任务用贵模型
- **Fallback 策略**：主模型失败自动切换到备选模型
- **Cost 追踪**：每次调用记录 token 消耗和成本

### 3.9 数据导出 (Exporter)
- **数据收集**：训练数据导出继续读取 Task / TaskExecution；执行质量反馈读取 EvalEvent。
- **数据脱敏**：导出前自动脱敏 PII 信息（`exporter/anonymizer.py`）
- **导出格式**：JSONL（`training_data`、`eval_events` / `evaluation`）
- **导出用途**：Agent 路由优化、Skill 模板优化、模型选择优化

### 3.9.1 Eval Feedback
- **EvalEvent**：记录 Stage、AgentProfile、ModelRoute、Skill、Artifact、Delivery、确认、耗时、成本和失败原因。
- **EvaluationService**：主链路非阻塞写入，失败只打日志，不阻断执行。
- **Evaluation API**：`GET /api/v1/evaluation/summary` 提供项目和时间范围维度聚合。
- **Dashboard**：显示阶段、Skill 和 Delivery 成功率与平均阶段耗时。

### 3.10 认证 (Auth)
- **JWT 工具**：access_token / refresh_token 签发与校验（`auth/jwt.py`）
- **权限管理**：角色权限校验（`auth/permissions.py`）
- **API Key**：服务间认证
- **中间件**：`middleware/auth.py` 自动校验请求认证

### 3.11 MCP 集成
- **MCP 客户端**：Model Context Protocol 客户端，Agent 可调用外部工具（`mcp/client.py`）
- **MCP 配置**：工具列表、传输层配置和 permissions 声明（`mcp/config.py`）
- **MCP RuntimeSpec**：MCP Server 注册为 `mcp_<server>` Skill，写入 `source_type=mcp`、`executor_kind=mcp` 和权限声明，复用 StageSkillPolicy 与 SkillDispatcher 治理。

### 3.12 Webhook 集成
- **Webhook 管理器**：事件驱动的外部通知（`webhooks/manager.py`）
- **审计日志**：`models/audit_log.py` 记录全量操作

## 4. 项目结构

```
src/
├── agent_forge/
│   ├── __init__.py
│   ├── config.py                # 全局配置（含沙箱环境变量）
│   ├── database.py              # 数据库连接 / session 工厂
│   ├── tracing.py               # 全链路 trace_id
│   ├── harness/                 # Harness 六层实现
│   │   ├── validator.py         # 第1层 输入校验
│   │   ├── router.py            # 第2层 路由分发
│   │   ├── registry.py          # 第3层 注册中心
│   │   ├── governance.py        # 第4层 容错治理
│   │   ├── executor.py          # 第5层 执行编排
│   │   └── memory.py            # 第6层 记忆状态
│   ├── bus/                     # 消息总线
│   │   ├── publisher.py         # Pub/Sub 广播 + SSE 流式输出
│   │   ├── consumer.py          # 点对点通信（Request/Response）
│   │   └── init.py              # 总线初始化
│   ├── agents/                  # Agent 实现
│   │   ├── base.py              # Agent 基类 + CodeAgent + AnalysisAgent + SearchAgent
│   │   ├── coder.py             # CoderAgent
│   │   └── resolver.py          # AgentProfile 运行时解析
│   ├── skills/                  # Skill 插件系统
│   │   ├── manager.py           # Skill 管理器
│   │   ├── loader.py            # 加载器
│   │   ├── registry.py          # 注册中心
│   │   ├── dispatcher.py        # 调度器
│   │   ├── engine.py            # 执行引擎
│   │   ├── builtin.py           # 内置 Skill 注册
│   │   ├── manifest.py          # 清单管理
│   │   ├── installer.py         # Skill 安装
│   │   ├── runtime_spec.py      # SkillRuntimeSpec 与权限归一化
│   │   ├── policy.py            # Skill 权限策略
│   │   ├── code_executor.py     # 代码执行 Skill（沙箱调用）
│   │   ├── http_request.py      # HTTP 请求 Skill
│   │   ├── web_search.py        # 网页搜索 Skill
│   │   ├── weather.py           # 天气查询 Skill
│   │   └── update_profile.py    # 个人信息 Skill
│   ├── memory/                  # 4 层记忆系统
│   │   ├── manager.py           # 记忆 CRUD
│   │   ├── embedder.py          # 向量化
│   │   ├── retriever.py         # 检索
│   │   ├── tasks.py             # 记忆相关后台任务
│   │   └── semantic_entry.py    # 语义记忆条目模型引用
│   ├── llm/                     # LLM Provider 抽象
│   │   ├── provider.py          # LiteLLM 适配 + Cost 追踪
│   │   └── router.py            # ModelRoute 解析
│   ├── pipeline/                # Pipeline Catalog + StageRuntime
│   ├── governance/              # GovernancePolicy
│   ├── delivery/                # 本地写回、GitHub PR、zip Delivery
│   ├── bridge/                  # 本地/上传 Mount 只读上下文
│   ├── evaluation/              # EvalEvent 记录与聚合
│   ├── exporter/                # 数据导出
│   │   ├── manager.py           # 导出任务管理
│   │   └── anonymizer.py        # PII 脱敏
│   ├── sandbox/                 # 沙箱执行层
│   │   ├── base.py              # Protocol 接口、数据类、异常
│   │   ├── factory.py           # SandboxProviderFactory
│   │   ├── manager.py           # SandboxManager（生命周期 + TTL）
│   │   ├── pool.py              # SandboxPool（热沙箱池）
│   │   ├── reclaimer.py         # SandboxReclaimer（TTL 自动回收）
│   │   ├── mock.py              # 已移除的 runtime mock 提示文件
│   │   ├── docker.py            # DockerSandboxExecutor
│   │   └── cubesandbox/         # CubeSandbox 实现
│   │       ├── e2b.py           # CubeSandboxE2BExecutor（E2B SDK）
│   │       └── api.py           # CubeSandboxAPIExecutor（REST API）
│   ├── models/                  # SQLAlchemy 数据模型
│   │   ├── base.py              # 模型基类
│   │   ├── user.py              # 用户
│   │   ├── agent.py             # Agent
│   │   ├── task.py              # 任务
│   │   ├── subtask.py           # 子任务
│   │   ├── task_execution.py    # 任务执行
│   │   ├── conversation.py      # 对话
│   │   ├── session.py           # 会话
│   │   ├── memory_entry.py      # 记忆条目
│   │   ├── user_memory.py       # 用户记忆
│   │   ├── semantic_entry.py    # 语义记忆条目
│   │   ├── skill.py             # Skill
│   │   ├── agent_skill.py       # Agent-Skill 绑定
│   │   ├── skill_install.py     # Skill 安装记录
│   │   ├── api_key.py           # API Key
│   │   ├── audit_log.py         # 审计日志
│   │   ├── export_task.py       # 导出任务
│   │   ├── project.py           # Project / ProjectMount / Artifact
│   │   ├── pipeline.py          # PipelineRun / PipelineStageState
│   │   ├── llm.py               # LLM Provider / Model / Credential / Route
│   │   ├── evaluation.py        # EvalEvent
│   │   ├── webhook.py           # Webhook
│   │   ├── user_agent_settings.py # 用户-Agent 设置
│   │   └── __init__.py          # 统一导出
│   ├── api/                     # 内部 API 路由（AgentForge 自管理）
│   │   ├── sse.py               # SSE 流式输出
│   │   └── routes/
│   │       ├── cost.py          # Cost 统计
│   │       ├── dashboard.py     # 仪表盘
│   │       ├── exports.py       # 数据导出
│   │       ├── skills.py        # Skill 管理
│   │       └── webhooks.py      # Webhook 管理
│   ├── auth/                    # 认证
│   │   ├── jwt.py               # JWT 工具
│   │   └── permissions.py       # 权限校验
│   ├── mcp/                     # MCP 集成
│   │   ├── client.py            # MCP 客户端 + RuntimeSpec 注册
│   │   └── config.py            # MCP 配置 + permissions 声明
│   └── webhooks/                # Webhook 集成
│       └── manager.py           # Webhook 管理器
├── api/                         # FastAPI 外部 API
│   ├── main.py                  # 应用入口 + lifespan
│   ├── schemas/                 # Pydantic Schema
│   │   ├── agent.py             # Agent Schema
│   │   └── task.py              # 任务 Schema
│   └── routes/
│       ├── agents.py            # Agent 管理
│       ├── auth.py              # 认证
│       ├── dashboard.py         # 仪表盘
│       ├── evaluation.py        # Evaluation summary
│       ├── health.py            # 健康检查
│       ├── llm.py               # LLM 配置
│       ├── memory.py            # 记忆 CRUD
│       ├── pipeline_catalog.py  # Pipeline Catalog
│       ├── pipeline_runs.py     # PipelineRun / StageState
│       ├── projects.py          # Project / Mount / Artifact / Delivery
│       ├── sandboxes.py         # 沙箱管理
│       ├── sessions.py          # 会话管理
│       ├── skills.py            # Skill 管理
│       ├── tasks.py             # 任务管理
│       ├── tools.py             # 工具
│       └── uploads.py           # 文件上传
└── middleware/                  # 中间件
    ├── auth.py                  # 认证中间件
    ├── rate_limit.py            # 限流中间件
    └── trace.py                 # 链路追踪中间件
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
                         └── CubeSandboxAPIExecutor

SandboxManager ── 沙箱生命周期 + TTL 管理
SandboxPool    ── 热沙箱池（预置、复用、降级冷启动）
SandboxReclaimer ── TTL 后台扫描 + 自动回收
```

> 单元测试使用 `tests/sandbox/fakes.py` 中的 `InMemorySandboxExecutor`，不再把 mock provider 注册进产品运行时。

### 8.2 核心组件

| 组件 | 文件 | 职责 |
|------|------|------|
| `SandboxExecutor` Protocol | `sandbox/base.py` | 统一接口（create/execute/destroy/pause/resume/files_read/files_write/connect/get_logs） |
| `SandboxConfig` | `sandbox/base.py` | 沙箱创建配置（template_id、timeout、memory、writable_layer、exposed_ports） |
| `ConnectInfo` | `sandbox/base.py` | 沙箱连接信息（sandbox_id、host、port、template_id、state、timeout_at） |
| `SandboxState` | `sandbox/base.py` | 状态枚举（PENDING / RUNNING / PAUSED / DESTROYED / TIMEOUT） |
| `ExecResult` | `sandbox/base.py` | 执行结果（stdout、stderr、exit_code、duration_ms） |
| `SandboxError` 家族 | `sandbox/base.py` | 7 种异常：SandboxError / SandboxUnavailableError / SandboxCreationError / SandboxDestroyedError / SandboxTimeoutError / SandboxAcquireTimeoutError / SandboxAuthError / FileAccessDeniedError |
| `SandboxProviderFactory` | `sandbox/factory.py` | 工厂，按 provider 名称（docker / cubesandbox / mock）创建对应 Executor |
| `SandboxManager` | `sandbox/manager.py` | 沙箱生命周期管理器（上下文协议，TTL 续期，失败降级） |
| `SandboxPool` | `sandbox/pool.py` | **热沙箱池** — 预置 + 复用 + 冷启动降级 |
| `SandboxReclaimer` | `sandbox/reclaimer.py` | TTL 自动回收器 — 后台协程扫描 + pause → destroy |

### 8.3 沙箱池（SandboxPool）详细设计

#### 设计理念

高并发场景下，每次按需创建沙箱的 ~60ms 冷启动延迟不可接受。
SandboxPool 通过**可选预热（bootstrap）→ 复用（acquire/release）→ 降级（cold-start）→ 清理（cleanup）** 四步循环，将热沙箱的获取延迟降至 ~0ms。

TASK-020 后，应用启动默认不预热远程沙箱，避免本地启动或测试时自动创建 E2B 云资源。生产环境如需要热池，必须显式设置 `SANDBOX_POOL_PREWARM_ENABLED=true`。

#### 生命周期

```
应用启动（仅 SANDBOX_POOL_PREWARM_ENABLED=true）
    │
    ▼
bootstrap() ── 预创建 min_size 个沙箱，放入 asyncio.Queue
    │
    ▼
请求到来 → acquire()
    │
    ├── 池中有热沙箱 ──> 直接从 Queue 取出（~0ms）
    │
    └── 池为空 ──> 冷启动 create()（~60ms）
    │
    ▼
executor.execute(sandbox_id, code)
    │
    ▼
release()
    │
    ├── 池未满 ──> cleanup() → 放回 Queue
    │
    └── 池已满 ──> destroy() 直接销毁
    │
    ▼
应用关闭 → drain() ── 销毁池中所有沙箱
```

#### 关键参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `SANDBOX_POOL_PREWARM_ENABLED` | false | 是否在应用启动时预热沙箱池 |
| `SANDBOX_POOL_MIN_SIZE` | 5 | 开启预热后启动时预创建的沙箱数量 |
| `SANDBOX_POOL_MAX_SIZE` | 20 | 池的最大容量，超出后 release 直接销毁 |
| `cleanup_timeout` | 5s | 归还前清理沙箱内状态的超时 |

#### 清理策略（cleanup）

在归还前清理沙箱内状态，确保下一个使用者看到干净环境：

1. 杀掉子进程（`/proc` 中 PID > 1 的进程）
2. 清除可写层中的临时数据（`/tmp`、`/root/.cache`、`/root/.local/lib`、`/home`）

> 注意：CubeSandbox 使用 CoW 可写层（writable layer），任何文件写入在 reuse 时都会残留，因此清理范围比 `/tmp` 更广。

#### 冷启动降级

Pool 本身不做熔断或限流。当池为空且无等待超时（`timeout=None`）时，直接走 `executor.create(config)` 冷启动路径——由上层 SandboxManager 处理降级（如 CubeSandbox 不可用时切换到 Docker）。

### 8.4 沙箱池（SandboxReclaimer）详细设计

#### 职责

后台协程定期扫描 Pool 中的沙箱，自动回收超时的沙箱，防止资源泄漏：

1. **扫描**：每 N 秒（默认 60s）检查池中每个沙箱的 `is_expired`
2. **销毁超时沙箱**：已超时的直接 destroy
3. **池满销毁**：未超时但池已满时，多余沙箱直接 destroy
4. **优雅关闭**：应用退出时 drain() 销毁全部

#### 关键参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `interval` | 60s | 扫描间隔 |
| `pause_ttl` | 120s | pause 后存活多久再 destroy（预留） |
| `max_size` | 10 | Reclaimer 自建池的上限 |

> Reclaimer 的 pool 默认 `min_size=0`（不预热），仅做回收；生产环境的预热由独立 `SandboxPool.bootstrap()` 负责。

### 8.5 Sandbox API 端点

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
| 数据库 | PostgreSQL + pgvector | SQLAlchemy 2.0 async + Alembic 迁移 |
| 认证 | JWT + API Key | 用户/服务间认证 |
| 重试 | tenacity | 指数退避 |
| 熔断 | pybreaker | 连续失败熔断 |
| 限流 | slowapi | Token Bucket |
| 沙箱 | CubeSandbox (KVM) + Docker | 分级隔离策略 |
| 向量检索 | pgvector | 语义记忆嵌入存储 |
| MCP | Model Context Protocol | Agent 外部工具集成 |
| 流式输出 | SSE (FastAPI) | 实时事件推送 |
