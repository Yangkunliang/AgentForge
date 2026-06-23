# CLAUDE.md

本文档为 Claude Code (claude.ai/code) 提供本仓库的开发指导。

## 项目概述

**AgentForge** — 通用多智能体协同框架，让 AI Agent 像有纪律的团队一样协作完成任务。

核心理念：**Agent = Model + Harness**，Harness 为 LLM 提供"让它真正能干活的工程支撑"。

> 当前落地场景：全栈开发自动化（代码审查、生成、研究）。框架本身领域无关，Skill 和 Agent 可按需替换以支持其他场景。

**当前状态：Phase 0 — 仅设计文档。** 本仓库目前只包含产品和技术设计文档，尚无实现代码（不存在 `src/`、`tests/`、`pyproject.toml`）。后续会话将根据这些文档进行实现。

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

所有设计文档位于 `docs/` 目录下，索引以 `docs/README.md` 为准。

| 目录 | 内容 |
|------|------|
| `docs/product/` | 产品需求（`PRD-v1.md`） |
| `docs/design/` | 架构、API 规范、数据库、安全、LLM 配置、数据导出、前端架构、RabbitMQ、部署 |
| `docs/tasks/` | 任务清单（`CHECKLIST.md`） |
| `docs/iteration/` | 迭代记录 |

根目录 `MEMORY.md` 也索引了所有文档。

---

## 架构概要

系统采用 **六层 Harness 架构**：

1. **Validator（校验层）** — 输入校验（Pydantic Schema、Prompt 注入检测、长度/类型约束）
2. **Router（路由层）** — 任务路由到 TaskOrchestrator
3. **Registry（注册中心）** — AgentRegistry + SkillRegistry + `skills/` 目录热加载
4. **Governance（容错治理）** — 重试（tenacity 指数退避，最多 3 次）、熔断器（pybreaker）、优雅降级
5. **Executor（执行编排）** — 任务分解（LLM）→ Agent 协商（Contract Net 协议）→ Skill 调用 → 结果合并
6. **Memory（记忆状态）** — 短期记忆（对话历史）、长期记忆（任务结果持久化）、审计日志（全链路 trace_id）

**支撑子系统**：消息总线（RabbitMQ，Pub/Sub 广播 + 点对点 + SSE 流式输出）、LLM Provider 抽象层（LiteLLM，支持模型路由/降级/Cost 追踪）、数据导出器（JSONL 训练数据 + PII 脱敏）。

### 计划技术栈

| 组件 | 选型 |
|------|------|
| 后端 | Python + FastAPI (async) |
| LLM 网关 | LiteLLM（统一多厂商 API + Cost 追踪） |
| 数据库 | PostgreSQL 15（SQLAlchemy 2.0 async + Alembic 迁移） |
| 消息队列 | RabbitMQ（持久化 + ACK + 死信队列，详见 `docs/design/RABBITMQ.md`） |
| 前端 | Vue 3 + Vite + Element Plus + Pinia（详见 `docs/design/FRONTEND-ARCHITECTURE.md`） |
| 认证 | JWT（access_token 1h）+ refresh_token（HttpOnly Cookie 7d）+ API Key |
| 重试 | tenacity（指数退避） |
| 熔断器 | pybreaker |
| 限流 | slowapi（Token Bucket）+ Redis |

### 计划项目结构

```
AgentForge/
├── src/
│   ├── agent_forge/
│   │   ├── harness/     # 六层 harness（validator, router, registry, governance, executor, memory）
│   │   ├── bus/         # 消息总线（pubsub, direct, init）
│   │   ├── agents/      # Agent 实现（基类 + 内置：coder, reviewer, researcher）
│   │   ├── skills/      # 插件系统（manager, loader, validator）
│   │   ├── models/      # SQLAlchemy 数据模型
│   │   ├── llm/         # LLM Provider 抽象（litellm_adapter, router, cost）
│   │   └── exporter/    # 数据导出（JSONL, 脱敏）
│   ├── api/             # FastAPI 路由（main.py + tasks, agents, skills, exports, dashboard, auth）
│   └── middleware/      # auth.py, rate_limit.py
└── web/                 # Vue 3 前端
    └── src/
        ├── api/         # Axios + SSE 客户端 + 自动生成类型
        ├── stores/      # Pinia 状态（auth, task, agent, skill）
        ├── composables/ # useSSE, useAuth, useSkillInstall
        └── views/       # 页面组件
```

---

## 开发工作流（实现阶段）

项目遵循文档驱动的迭代链条：**PRD → Task → Design → Test → Iteration**。

实现任务清单见 `docs/tasks/CHECKLIST.md`，按 P1 → P2 → P3 → P4 顺序执行，每完成一项勾选并单独 commit。

实现后预期命令：

```bash
# 依赖服务
docker compose up -d              # 启动 PostgreSQL + RabbitMQ + Redis

# 后端
alembic upgrade head              # 数据库迁移
PYTHONPATH=/Users/yangkl/AgentForge/src uvicorn api.main:app --reload --port 8000  # 启动 API

# 前端
cd web
npm run gen:types                 # 同步后端 API 类型（后端须先启动）
npm run dev                       # 启动前端（localhost:3000）

# 代码质量
ruff check src/
mypy src/
pytest tests/ -v
```

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

- 目前无实现代码，重点在设计文档（`docs/design/` 下 9 个文档已完备）
- 实现任务清单：`docs/tasks/CHECKLIST.md`
- 本地开发启动顺序：`docs/design/DEPLOYMENT.md` 第 3 节
- 安全模型：双认证（JWT + API Key）、Prompt 注入防护、Skill 沙箱、全链路 trace_id 审计
