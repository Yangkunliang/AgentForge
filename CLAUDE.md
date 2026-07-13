# CLAUDE.md

本文档为 Claude Code (claude.ai/code) 提供本仓库的开发指导。

## 项目概述

**AgentForge** — 通用多智能体协同框架，让 AI Agent 像有纪律的团队一样协作完成任务。

核心理念：**Agent = Model + Harness**，Harness 为 LLM 提供"让它真正能干活的工程支撑"。

> 当前落地场景：全栈开发自动化（代码审查、生成、研究）。框架本身领域无关，Skill 和 Agent 可按需替换以支持其他场景。

**当前状态：Phase 1 — 记忆系统已实现；Project / Mount / Artifact 数据底座已实现；PipelineRun / StageState 阶段状态机已实现；Artifact 归档、查看和上下文复用已实现；人工确认与阶段继续机制已实现；Agent Bridge 授权文件上下文已实现；Delivery diff 预览与确认写回已实现；GitHub OAuth Mount 授权底座已实现；GitHub PR Delivery 已实现；zip Delivery Package 已实现；Upload Mount 上下文兜底已实现；AI Runtime 收敛架构基线已完成；Pipeline Stage Catalog 后端事实源已实现；AgentProfile 运行时绑定已实现；ModelRoute 运行时绑定与 LLM 结构化配置已实现；第三方 Skill 导入、权限、运行时注册和审计闭环已实现；Governance 人工确认策略引擎已实现；Eval Feedback 结构化反馈闭环已实现；AI Runtime 架构文档收敛已完成；Stage 级 SkillPolicy 编排已实现；MCP RuntimeSpec 权限归一已实现；内置 Skill RuntimeSpec 补齐已实现；高风险 Skill 阶段级临时授权已实现；高风险 Skill 授权确认入口已实现；高风险 Skill 授权 Eval 可观测性已实现；高风险 Skill 授权聚合指标已实现；Dashboard 高风险 Skill 授权指标已实现；Dashboard 路由单一事实源已实现；Artifact 运行时来源固化已实现。** 核心实现位于 `src/agent_forge/`，数据库迁移见 `migrations/alembic/`。记忆系统详见 `docs/tech-design/DATABASE.md` 第 5 节，核心闭环详见 `docs/architecture/CORE-DEV-WORKFLOW.md`，AI Runtime 收敛主线详见 `docs/architecture/AI-RUNTIME-CONVERGENCE.md`。

---

## 产品定位（必读）

**AgentForge 是一个面向「全栈开发工程师」的平台产品，不是开发者自用工具。**

### 目标用户

付费使用 AgentForge 的是各自有独立项目的全栈开发工程师，典型场景包括：

- **独立开发者**：维护自己的 SaaS 产品，前后端可能在不同目录
- **创业团队成员**：多个微服务 / Monorepo，需要跨服务理解代码
- **外包接单开发者**：同时维护多个客户项目，需要快速切换项目上下文

### 核心产品模型

| 概念 | 说明 |
|------|------|
| **项目（Project）** | 用户自己的代码库，是平台的一等公民。每个用户可管理多个项目。 |
| **代码库上下文** | 用户通过 CLI 工具（`agentforge mount`）或桌面客户端授权 Agent 访问其本地目录，或通过 GitHub OAuth 连接远程仓库。 |
| **对话（Session）** | 归属于某个项目，历史产物（PRD、代码、测试报告）与项目绑定，可跨会话继续。 |
| **需求类型路由** | Agent 接收需求后先做意图分类，动态决定走哪几个阶段，不强制走完整 8 步流水线。 |
| **开发闭环** | Project → Mount → Session → PipelineRun → StageState → Artifact → Delivery，是全栈开发自动化的 MVP 主链路。 |

### 需求类型 → 流水线映射

| 类型 | 触发信号 | 走的阶段 | 跳过的阶段 |
|------|---------|---------|-----------|
| 全新功能 | 涉及新表、新路由、跨模块 | 全部 8 步 | 无 |
| 迭代优化 | 改现有逻辑、不加新表、范围局部 | 需求 Diff → 影响评估 → 开发 → 回归测试 | 完整 PRD、架构设计、UI 原型、任务拆解 |
| UI 调整 | 只改前端文件、不动接口和数据库 | 原型 Diff → 前端开发 → 视觉验收 | 需求分析、架构、DB、API、后端、任务拆解 |
| Bug / 重构 | 明确报错 / 性能问题 / 代码坏味道 | 问题定位 → 影响范围 → 修复 → 回归测试 | 需求分析、架构设计、UI 原型、任务拆解 |

### 不要做的假设

- ❌ 不要假设用户的项目是 AgentForge 自身的源码
- ❌ 不要假设用户只有一个项目
- ❌ 不要把「全栈工程师」理解为开发 AgentForge 的工程师，他们是平台的终端用户
- ❌ 不要在没有用户明确指令的情况下自动读取或修改用户代码库
- ❌ 不要对所有需求默认走完整 8 步流水线，先分类再规划

---

## 文档索引

### 索引源

- **Claude Code 快速索引**（本文档 § 文档速查）— 按路径列出每篇文档的一句话说明，供 Agent 快速定位
- `docs/README.md` — 文档体系总目录（版本历史、迭代链条说明）
- `docs/tasks/CHECKLIST.md` — 实现任务清单（P1→P4 优先级）
- 根目录 `MEMORY.md` — 项目上下文索引（开发约定、关键文件路径）

### 文档速查

| 路径 | 一句话说明 |
|------|-----------|
| `docs/tech-design/ARCHITECTURE.md` | 整体架构、Harness 六层、消息总线、执行流程、沙箱池 |
| `docs/tech-design/API-SPEC.md` | 完整 API 规范（Project、Mount、Pipeline Catalog、PipelineRun、StageState、Artifact、Delivery、Evaluation、认证、任务、Agent、Skill、Dashboard、Cost、SSE、Webhook、导出） |
| `docs/tech-design/DATABASE.md` | 数据库实体、Project/Mount/PipelineRun/StageState/Artifact/Delivery/EvalEvent 核心闭环表 + 记忆系统表（semantic_entries、user_memories、pgvector 全文索引） |
| `docs/tech-design/SECURITY.md` | 认证体系、限流、Prompt 注入防护（三类注入 + 语义检测）、Skill 沙箱分级、审计日志 |
| `docs/tech-design/LLM-CONFIG.md` | LLM Provider 接口、配置管理、两级 Prompt、Thinking 拆分、ReAct tool_use 循环、Cost 追踪 |
| `docs/tech-design/FRONTEND-ARCHITECTURE.md` | Vue 3 前端架构（SSE 方案、Token 策略、权限模型、Store 同步） |
| `docs/tech-design/RABBITMQ.md` | 消息队列拓扑、Exchange/Queue 设计、消息格式、死信处理 |
| `docs/tech-design/DEPLOYMENT.md` | 本地开发环境、生产部署、Nginx 配置、数据库迁移 |
| `docs/tech-design/SANDBOX-RESEARCH.md` | 沙箱机制调研报告（Docker vs CubeSandbox 对比） |
| `docs/tech-design/INTEGRATION-CUBESANDBOX.md` | CubeSandbox 集成设计（E2B SDK / REST API、API 设计、分级策略） |
| `docs/tech-design/DATA-EXPORT.md` | 训练数据导出（JSONL）、PII 脱敏策略 |
| `docs/tech-design/SSE-EXECUTION-VISUALIZATION.md` | SSE 执行可视化方案 |
| `docs/architecture/AGENT-MODEL.md` | Agent 领域模型（类型、能力、Contract Net 协作机制）— **产品定义**，非仓库工作规范 |
| `docs/architecture/CORE-DEV-WORKFLOW.md` | 核心开发闭环（Project、Mount、Session、PipelineRun、StageState、Artifact、Delivery） |
| `docs/architecture/AI-RUNTIME-CONVERGENCE.md` | AI Runtime 收敛主线（Project、Intent、Pipeline、Stage、AgentProfile、ModelRoute、SkillRuntime、Governance、EvalFeedback） |
| `docs/product-design/PRD-全栈Agent交互体验-20260623.md` | 项目管理、意图路由、阶段感知对话、快捷动作、Agent Bridge |
| `docs/product-design/PRD-CLAW-集成能力层-20260622.md` | CLAW 集成能力层（Skill / MCP / ClaWHub 市场） |
| `docs/product-design/PRD-多智能体框架-20260617.md` | 产品定位、用户故事、核心功能、技术栈 |
| `docs/tasks/CHECKLIST.md` | 实现任务清单、核心开发闭环覆盖矩阵、TASK-012～TASK-019 后续路线图 |
| `docs/standards/ITERATION-STANDARD.md` | 迭代目录命名、产物规范、小步提交、Skill 使用策略 |
| `docs/standards/DEVELOPMENT-GUIDE.md` | 环境配置、启动步骤、测试方法、开发规范 |
| `docs/iterations/` | 迭代记录（按日期/主题建目录） |

### 关键代码文件速查

| 路径 | 说明 |
|------|------|
| `src/agent_forge/llm/provider.py` | LLM Provider 抽象（complete/stream/tool_use + Thinking 拆分 + Tracing） |
| `src/agent_forge/llm/router.py` | StageRuntime 使用的 ModelRoute 解析器，支持结构化 route、fallback 和 legacy settings |
| `src/agent_forge/config.py` | 全局配置（Pydantic Settings，含 LLM/DB/RabbitMQ/Sandbox） |
| `src/agent_forge/skills/engine.py` | ReAct 执行引擎（多轮 tool_use 循环） |
| `src/agent_forge/skills/manager.py` | Skill 插件管理器 |
| `src/agent_forge/skills/manifest.py` | 第三方 Skill Manifest 解析，支持 `agentforge-skill.yaml` 和兼容 `skill.md` |
| `src/agent_forge/skills/builtin.py` | 内置 Skill 注册和 `source_type=builtin` RuntimeSpec 生成 |
| `src/agent_forge/skills/runtime_spec.py` | SkillRuntimeSpec、权限归一化和风险分级 |
| `src/agent_forge/skills/policy.py` | Skill 调用权限策略 |
| `src/agent_forge/skills/dispatcher.py` | Skill 调用分发、权限校验、审计和 skill_eval 事件 |
| `src/agent_forge/mcp/config.py` | MCP Server 传输配置和 permissions 声明；未声明权限默认高风险 |
| `src/agent_forge/mcp/client.py` | MCP 连接池、tool_defs 转换、`source_type=mcp` RuntimeSpec 注册 |
| `src/agent_forge/agents/base.py` | Agent 基类 + CodeWriterAgent/AnalysisAgent/SearchAgent + create_agent |
| `src/agent_forge/agents/coder.py` | CoderAgent |
| `src/agent_forge/agents/resolver.py` | StageRuntime 使用的 AgentProfile 解析器，支持用户覆盖、项目默认、阶段默认和系统默认 |
| `src/agent_forge/memory/` | 4 层记忆实现 |
| `src/agent_forge/models/` | SQLAlchemy 数据模型（含 Project、ProjectMount、OAuthCredential、OAuthState、PipelineRun、PipelineStageState、Artifact、LLM Provider/Model/Credential/Route、EvalEvent 核心闭环表） |
| `src/agent_forge/pipeline/` | Pipeline Catalog、intent 阶段定义、状态机服务与 StageRuntime |
| `src/agent_forge/bridge/` | Agent Bridge 授权本地 Mount、Upload Mount 文件列表和只读读取安全边界 |
| `src/agent_forge/delivery/` | Artifact diff preview、确认写回授权 Mount、GitHub PR Delivery、zip Delivery Package、Delivery report |
| `src/agent_forge/evaluation/` | EvalEvent 记录与摘要聚合服务，供 Runtime、Dashboard 和 Export 使用 |
| `src/agent_forge/integrations/github.py` | GitHub OAuth URL、token exchange 和 repo metadata helper |
| `src/agent_forge/security/credentials.py` | 服务端凭据加密/解密 helper，供 OAuth token 存储使用 |
| `src/agent_forge/cli.py` | `agentforge mount <path>` CLI 入口 |
| `src/agent_forge/tracing.py` | 分布式 tracing（span 装饰器 + 结构化 JSON 日志） |
| `api/main.py` | FastAPI 入口 |
| `api/api.py` | 路由注册 |

---

## 架构概要

系统采用 **六层 Harness 架构**：

1. **Validator（校验层）** — 输入校验（Pydantic Schema、Prompt 注入检测、长度/类型约束）
2. **Router（路由层）** — 任务路由到 TaskOrchestrator
3. **Registry（注册中心）** — AgentRegistry + SkillRegistry + `skills/` 目录热加载
4. **Governance（容错治理）** — 重试（tenacity 指数退避，最多 3 次）、熔断器（pybreaker）、优雅降级
5. **Executor（执行编排）** — 任务分解（LLM）→ Agent 协商（Contract Net 协议）→ Skill 调用 → 结果合并
6. **Memory（记忆状态）** — 4 层记忆架构（Working/Episodic/Semantic/User），详见 `src/agent_forge/memory/` 和 `docs/tech-design/DATABASE.md` 第 5 节

**支撑子系统**：消息总线（RabbitMQ，Pub/Sub 广播 + 点对点 + SSE 流式输出）、LLM Provider 抽象层（LiteLLM，支持模型路由/降级/Cost 追踪）、Eval Feedback（结构化执行事件 + Dashboard 聚合 + JSONL 导出）、数据导出器（JSONL 训练数据 + PII 脱敏）。

**核心开发闭环**：面向全栈开发工程师的产品主线是 `Project -> Mount -> Session -> PipelineRun -> StageState -> Artifact -> Delivery -> Eval Feedback`。TASK-013 已实现 Project / Mount / Artifact 数据底座与项目维度 Session API；TASK-014 已完成项目管理页、创建向导、ProjectBar 和 Chat Session 的真实 Project API 接入；TASK-015 已实现 PipelineRun / StageState 状态机、StageRuntime 和 StagePreview 后端状态渲染；TASK-016 已实现阶段 Artifact 自动归档、Chat / Project / Viewer 查看和上下文复用；TASK-017 已实现 `waiting_confirmation`、ConfirmCard、确认 API、确认 SSE 和审计日志；TASK-018 已实现 `agentforge mount`、Bridge 状态/文件列表/读取 API、ContextPicker 授权文件选择和真实文件内容注入 SkillExecutionEngine；TASK-019 已实现 Artifact diff preview、`confirm_write` 写回 connected local Mount、写前备份、Delivery report 和 Markdown 导出；TASK-023 已实现 GitHub OAuth Mount 授权底座，token 服务端加密存储，callback 通过一次性 state 绑定用户和项目，ProjectMount 只保存非敏感 repo metadata 和 credential 引用；TASK-024 已实现 GitHub PR Delivery preview/apply、`expected_base_sha` 二次校验、branch/commit/PR 创建、失败报告和审计；TASK-025 已实现 zip Delivery preview/apply/download、manifest、sha256、下载权限和过期清理；TASK-026 已实现 Upload Mount multipart 上传、manifest 范围读取、ContextPicker 文件源和 Chat 上下文注入；TASK-027 已完成 AI Runtime 收敛架构基线；TASK-028 已实现后端 Pipeline Catalog，使 StageRuntime、PipelineService 和前端 Pipeline Store 消费同一份 StageDefinition；TASK-029 已实现 AgentResolver、StageState agent_profile 追踪、运行时 Agent 候选 API 和 AgentSkill allowlist；TASK-030 已实现 ModelRouter、LLM Provider/Model/Credential/Route 配置、Credential 脱敏和 StageState model route 追踪；TASK-031 已实现第三方 Skill Manifest 预览、安装、权限策略、SkillRegistry runtime spec 和调用审计；TASK-032 已实现 GovernancePolicy、确认原因/影响范围落库、Delivery 未确认拒绝上下文、高风险 Skill 调用治理审计和 ConfirmCard 策略展示；TASK-033 已实现 EvalEvent、EvaluationService、Evaluation API、Dashboard 指标和 Eval JSONL 导出；TASK-034 已完成 AI Runtime 架构文档收敛；TASK-035 已实现 Stage 级 SkillPolicy 编排，StageRuntime 会在调用 SkillExecutionEngine 前过滤 LLM 可见工具；TASK-036 已实现 MCP RuntimeSpec 权限归一，MCP 外部工具也会复用 StageSkillPolicy 和 SkillDispatcher 权限治理；TASK-037 已实现内置 Skill RuntimeSpec 补齐，默认仅暴露 `web_search` 和 `get_weather`；TASK-038 已实现 `advanced_context.skill_authorization` 阶段级临时授权，允许用户确认后在当前阶段放行指定高风险 Skill，且不会绕过 AgentSkill allowlist；TASK-039 已实现 `skill_authorization_required` SSE 和 Chat 授权卡片，用户可确认后以一次性授权 payload 重试；TASK-040/TASK-041 已将授权请求、授权使用和授权聚合指标纳入 Eval Feedback；TASK-042 已将授权指标接入 Dashboard 可视化；TASK-043 已将 Dashboard 路由收敛到真实 `api.routes.dashboard` 单一事实源；TASK-044 已将 Artifact 生成来源固化到 `metadata.runtime` 并在详情页展示 Agent、模型和路由。

### 计划技术栈

| 组件 | 选型 |
|------|------|
| 后端 | Python + FastAPI (async) |
| LLM 网关 | LiteLLM（统一多厂商 API + Cost 追踪） |
| 数据库 | PostgreSQL 15 + pgvector（SQLAlchemy 2.0 async + Alembic 迁移） |
| 消息队列 | RabbitMQ（持久化 + ACK + 死信队列，详见 `docs/tech-design/RABBITMQ.md`） |
| 前端 | Vue 3 + Vite + Element Plus + Pinia（详见 `docs/tech-design/FRONTEND-ARCHITECTURE.md`） |
| 认证 | JWT（access_token 1h）+ refresh_token（HttpOnly Cookie 7d）+ API Key |
| 重试 | tenacity（指数退避） |
| 熔断器 | pybreaker |
| 限流 | slowapi（Token Bucket）+ Redis |

### 计划项目结构

完整项目结构见 `docs/tech-design/ARCHITECTURE.md` 第 3.7 节。

---

## 开发工作流（实现阶段）

项目遵循文档驱动的迭代链条：**PRD → Task → Design → Test → Iteration**。

实现任务清单见 `docs/tasks/CHECKLIST.md`，按 P1 → P2 → P3 → P4 顺序执行，每完成一项勾选并单独 commit。

本地开发完整步骤详见 `docs/standards/DEVELOPMENT-GUIDE.md`。

---

## 关键设计决策

- **Harness Engineering 理念** — 将 Model 智能与工程支撑分离，框架领域无关
- **Skill 格式**：`skill.md`（LLM 指令，Claude Code 风格）+ `executor.py`（程序化调用入口）
- **Contract Net 协议** — Agent 协商机制（发布招标 → 竞标 → 评分 → 签约 → 执行 → 上报）
- **SSE 方案**：使用 `fetch + ReadableStream`，不用原生 `EventSource`（不支持自定义 Header）
- **Token 策略**：access_token 存 localStorage（Axios 可读），refresh_token 存 HttpOnly Cookie（JS 不可读）
- **类型同步**：`openapi-typescript` 从 FastAPI `/openapi.json` 自动生成前端类型，禁止手写

---

## 架构变更自动同步

对话中产生架构级别变更（模块增删、接口变更、数据模型调整、技术选型变更、部署架构变更）时，**必须主动同步更新**相关架构文档（`docs/architecture/`）、`MEMORY.md` 和本文件，无需用户额外指示。

bug 修复、小功能增强、样式调整等非架构变更不触发。

详见 `AGENTS.md` 第 7 节。

---

## 使用本仓库

- 核心实现：`src/agent_forge/`（记忆、引擎、消息总线、LLM 抽象）
- 前端：`web/src/`
- 数据库迁移：`migrations/alembic/versions/`
- 测试：`tests/`
- 技术设计文档：`docs/tech-design/`
- 本地开发启动顺序：`docs/tech-design/DEPLOYMENT.md` 第 3 节
- 安全模型：双认证（JWT + API Key）、Prompt 注入防护、Skill 沙箱、全链路 trace_id 审计
