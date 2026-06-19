# AgentForge

**AgentForge** — 面向生产的多智能体协同框架。

**当前重心**：全栈开发自动化。

## 项目结构

```
AgentForge/
├── docs/
│   ├── product/       # 产品文档
│   ├── design/        # 技术设计文档
│   └── iteration/     # 迭代记录
├── CLAUDE.md          # 开发指导
└── MEMORY.md          # 项目记忆
```

## 文档索引

| 目录 | 内容 |
|------|------|
| `docs/product/` | 产品需求（PRD） |
| `docs/design/` | 架构、API、数据库、安全、LLM 配置等设计文档 |
| `docs/iteration/` | 迭代记录 |

详细文档请查看 [docs/README.md](docs/README.md)。

## 核心特性

- **多 Agent 协同**：基于 Contract Net 协议的 Agent 间动态协商与任务分配
- **六层 Harness 架构**：Validator、Router、Registry、Governance、Executor、Memory
- **Skill 插件系统**：支持热加载的 Skill 扩展机制
- **全链路追踪**：端到端的 trace_id 审计与监控

## 技术栈

| 组件 | 选型 |
|------|------|
| 后端 | Python + FastAPI |
| 数据库 | PostgreSQL |
| 消息队列 | RabbitMQ |
| LLM 网关 | LiteLLM |
