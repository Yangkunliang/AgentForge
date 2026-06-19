# CLAUDE.md

本文档为 Claude Code (claude.ai/code) 提供本仓库的开发指导。

## 项目概述

**AgentForge** — 面向全栈开发者的多智能体协同工作框架，让 AI Agent 像人类团队一样协作完成任务。核心理念：**Agent = Model + Harness**，Harness 为 LLM 提供"让它真正能干活的工程支撑"。

**当前状态：Phase 0 — 仅设计文档。** 本仓库目前只包含产品和 Technical 设计文档，尚无实现代码（不存在 `src/`、`tests/`、`pyproject.toml`）。后续会话将根据这些文档进行实现。

## 文档索引

所有设计文档位于 `docs/` 目录下，索引以 `docs/README.md` 为准。

| 目录 | 内容 |
|------|------|
| `docs/product/` | 产品需求（`PRD-v1.md`） |
| `docs/design/` | 架构、API 规范、数据库、安全、LLM 配置、数据导出 |
| `docs/iteration/` | 迭代记录（`ITER-{task-name}-{timestamp}.md`） |
| `docs/api/` | API 文档（空 — 实现时补充） |

仓库根目录的 `MEMORY.md` 也链接了所有文档。

## 架构概要

系统采用 **六层 Harness 架构**：

1. **Validator（校验层）** — 输入校验（Pydantic Schema、Prompt 注入检测、长度/类型约束）
2. **Router（路由层）** — 任务路由到 TaskOrchestrator
3. **Registry（注册中心）** — AgentRegistry + SkillRegistry + `skills/` 目录热加载
4. **Governance（容错治理）** — 重试（tenacity 指数退避，最多 3 次）、熔断器（pybreaker）、优雅降级
5. **Executor（执行编排）** — 任务分解（LLM）→ Agent 协商（Contract Net 协议）→ Skill 调用 → 结果合并
6. **Memory（记忆状态）** — 短期记忆（对话历史）、长期记忆（任务结果持久化）、审计日志（全链路 trace_id）

**支撑子系统**：消息总线（Pub/Sub 广播 + Request/Response 点对点 + SSE 流式输出）、LLM Provider 抽象层（LiteLLM 适配器，支持模型路由/降级/Cost 追踪）、数据导出器（JSONL 训练数据 + PII 脱敏）。

### 计划技术栈

| 组件 | 选型 |
|------|------|
| 后端 | Python + FastAPI (async) |
| LLM 网关 | LiteLLM（统一多厂商 API + Cost 追踪） |
| 数据库 | PostgreSQL 15（SQLAlchemy 2.0 async + Alembic 迁移） |
| 消息队列 | RabbitMQ（持久化 + ACK + 死信队列） |
| 认证 | JWT + API Key |
| 重试 | tenacity（指数退避） |
| 熔断器 | pybreaker |
| 限流 | slowapi（Token Bucket） |

### 计划项目结构

```
src/
├── agentforge/
│   ├── harness/     # 六层 harness（validator, router, registry, governance, executor, memory）
│   ├── bus/         # 消息总线（pubsub, direct）
│   ├── agents/      # Agent 实现（基类 + 内置：coder, reviewer, researcher）
│   ├── skills/      # 插件系统（manager, loader, validator）
│   ├── models/      # 数据模型
│   ├── llm/         # LLM Provider 抽象（provider, litellm_adapter, config）
│   └── exporter/    # 数据导出（JSONL, 脱敏）
├── api/             # FastAPI 路由（main.py + tasks, agents, skills, exports）
└── middleware/      # auth.py, rate_limit.py
```

## 开发工作流（实现阶段）

项目遵循文档驱动的迭代链条：**PRD → Task → Design → Test → Iteration**。

实现后预期命令：
- **构建**: `python -m build`（通过 pyproject.toml 的 PEP 621）
- **Lint**: `ruff check src/`
- **类型检查**: `mypy src/`
- **测试**: `pytest tests/ -v`
- **单文件测试**: `pytest tests/test_file.py::test_name -v`
- **数据库迁移**: `alembic upgrade head`
- **本地数据库**: `docker compose up -d db`（PostgreSQL 15, 端口 5432）
- **运行 API**: `uvicorn src.api.main:app --reload`

（以上命令为占位符 — 实际命令以实施时的实现为准。）

## 关键设计决策（来自 ITER-001）

- **Harness Engineering 理念** — 将 Model 智能与工程支撑分离
- **Skill 格式**：Markdown 指令文件（`skill.md`）+ Python 执行（`executor.py`），受 Claude Code skill-creator 启发
- **PostgreSQL** 统一开发/生产环境（可 Docker Compose 启动）
- **Contract Net 协议** — Agent 协商机制（发布 → 竞标 → 评分 → 签约 → 评估）
- Skill.md 是面向 LLM 的 Claude Code 风格 Prompt 指令；executor.py 是程序化调用入口

## 使用本仓库

- 目前无实现代码，重点在设计文档
- 开始实现后，核心包位于 `src/agentforge/`
- 数据库使用 Docker Compose 本地启动（详见 `docs/design/DATABASE.md` §4.1）
- 安全模型：双认证（JWT 用户认证 + API Key 服务间认证）、Prompt 注入防护、Skill 沙箱、全链路 trace_id 审计
