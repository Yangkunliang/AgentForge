# AgentForge

**AgentForge** — 通用多智能体协同框架，让 AI Agent 像有纪律的团队一样协作完成任务。

**核心理念**：**Agent = Model + Harness**，Harness 为 LLM 提供"让它真正能干活的工程支撑"。

**当前落地场景**：全栈开发自动化（代码审查、生成、研究）。框架本身领域无关，Skill 和 Agent 可按需替换以支持其他场景。

**当前状态**：Phase 1 — 记忆系统已实现。详见 [docs/tasks/CHECKLIST.md](docs/tasks/CHECKLIST.md)。

---

## 产品定位

AgentForge 是一个面向**全栈开发工程师**的平台产品。每个用户可管理多个项目，每个对话归属于某个项目，历史产物（PRD、代码、测试报告）与项目绑定，可跨会话继续。

**需求类型路由**：Agent 收到需求后先做意图分类，动态决定走哪几个阶段，不强制走完整 8 步流水线。

| 需求类型 | 走的阶段 |
|---------|---------|
| 全新功能 | 全部 8 步 |
| 迭代优化 | 需求 Diff → 影响评估 → 开发 → 回归测试 |
| UI 调整 | 原型 Diff → 前端开发 → 视觉验收 |
| Bug / 重构 | 问题定位 → 影响范围 → 修复 → 回归测试 |

## 项目结构

```
AgentForge/
├── src/
│   ├── agent_forge/     # 核心框架
│   │   ├── harness/     # 六层 Harness（Validator、Router、Registry、Governance、Executor）
│   │   ├── bus/         # 消息总线（RabbitMQ, Pub/Sub + SSE 流式输出）
│   │   ├── agents/      # Agent 实现（基类 + 内置 Agent）
│   │   ├── skills/      # 插件系统（热加载 Skill 扩展机制）
│   │   ├── memory/      # 4 层记忆（Working/Episodic/Semantic/User）
│   │   ├── llm/         # LLM Provider 抽象（LiteLLM, 模型路由/Cost 追踪）
│   │   ├── exporter/    # 数据导出（JSONL, PII 脱敏）
│   │   ├── sandbox/     # 沙箱执行层（CubeSandbox E2B SDK / Pool / Reclaimer）
│   │   ├── api/         # 内部 API 层
│   │   ├── auth/        # 认证（JWT + API Key）
│   │   ├── mcp/         # MCP 集成
│   │   └── webhooks/    # Webhook 集成
│   ├── api/             # FastAPI 路由（main.py + 各模块路由）
│   └── middleware/      # auth.py, rate_limit.py
├── web/                 # Vue 3 前端（Element Plus + Pinia + SSE）
├── migrations/          # Alembic 数据库迁移
├── tests/               # 单元测试 + 集成测试
├── docs/                # 设计文档
│   ├── product-design/  # 产品需求文档
│   ├── tech-design/     # 技术设计文档
│   ├── architecture/    # 架构蓝图
│   ├── standards/       # 长期规范
│   └── iterations/      # 迭代记录
├── AGENTS.md            # 仓库级 Agent 工作规范
├── CLAUDE.md            # Claude Code 开发指导
└── MEMORY.md            # 项目记忆索引
```

## 核心特性

- **六层 Harness 架构**：Validator（输入校验）→ Router（任务路由）→ Registry（Agent/Skill 注册）→ Governance（重试/熔断）→ Executor（执行编排）→ Memory（4 层记忆）
- **需求类型路由**：根据意图分类动态组合流水线阶段，不强制走完整流程
- **Skill 插件系统**：支持热加载的 Skill 扩展机制（`skill.md` + `executor.py` 格式）
- **4 层记忆系统**：Working / Episodic / Semantic / User 记忆，持久化到 PostgreSQL
- **全链路追踪**：端到端的 trace_id 审计与监控
- **SSE 流式输出**：10 种事件类型，fetch + ReadableStream 实现
- **LLM Provider 抽象**：LiteLLM 统一多厂商 API，支持模型路由、降级与 Cost 追踪
- **LiteLLM Proxy Server**：独立部署的管理后台，`/ui/liteLLM` Dashboard 可视化 token 用量、Cost 趋势、模型路由配置与限流告警（部署后访问 `http://localhost:4000/ui/liteLLM`）
- **沙箱执行层**：CubeSandbox（E2B SDK v1 兼容，KVM 内核级隔离）+ Docker 分级策略；`SandboxPool` 热沙箱池降低冷启动延迟，`SandboxReclaimer` 后台协程 TTL 自动回收
- **数据导出**：JSONL 训练数据导出 + 三级 PII 脱敏策略

## 技术栈

| 组件 | 选型 |
|------|------|
| 后端 | Python + FastAPI (async) |
| LLM 网关 | LiteLLM（统一多厂商 API + Cost 追踪） |
| 管理后台 | LiteLLM Proxy Server | `/ui/liteLLM` Dashboard，token/Cost/路由监控 |
| 数据库 | PostgreSQL 15 + pgvector（SQLAlchemy 2.0 async + Alembic） |
| 消息队列 | RabbitMQ（持久化 + ACK + 死信队列 + SSE 流式输出） |
| 前端 | Vue 3 + Vite + Element Plus + Pinia |
| 认证 | JWT（access_token 1h + refresh_token HttpOnly Cookie 7d）+ API Key |
| 重试 | tenacity（指数退避） |
| 熔断器 | pybreaker |
| 限流 | slowapi（Token Bucket）+ Redis |
| 沙箱 | CubeSandbox（E2B SDK v1）+ Docker | KVM 内核级隔离 + 容器隔离，分级策略 |

## 文档索引

详细文档请查看 [docs/README.md](docs/README.md)。

### 快速链接

| 文档 | 说明 |
|------|------|
| [架构设计](docs/tech-design/ARCHITECTURE.md) | 整体架构、六层 Harness、执行流程 |
| [数据库设计](docs/tech-design/DATABASE.md) | 数据模型与表结构（含记忆系统） |
| [API 规范](docs/tech-design/API-SPEC.md) | API 端点设计 |
| [安全设计](docs/tech-design/SECURITY.md) | 认证、授权、限流策略 |
| [LLM 配置](docs/tech-design/LLM-CONFIG.md) | LLM Provider、模型路由、Cost 追踪 |
| [前端架构](docs/tech-design/FRONTEND-ARCHITECTURE.md) | 前端架构、SSE 方案、Token 策略 |
| [消息队列](docs/tech-design/RABBITMQ.md) | RabbitMQ 拓扑、Exchange/Queue 设计 |
| [部署指南](docs/tech-design/DEPLOYMENT.md) | 本地开发、生产部署、Nginx 配置 |

## 参考

- [LiteLLM](https://github.com/BerriAI/litellm) — 多厂商 LLM 统一 API + Cost 追踪
- [LiteLLM Proxy Server](https://github.com/BerriAI/litellm/tree/main/proxy) — 管理后台，`/ui/liteLLM` Dashboard
- [CubeSandbox](https://github.com/TencentCloud/CubeSandbox) — 腾讯开源，E2B 兼容，KVM 内核级隔离沙箱
