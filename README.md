# AgentForge

**AgentForge** — 面向生产的多智能体协同框架。

**当前重心**：全栈开发自动化。

## 项目结构

```
AgentForge/
├── docs/
│   ├── standards/      # 长期规范：文档、迭代、Skill 使用策略
│   ├── architecture/   # 当前系统架构蓝图
│   ├── product-design/   # 产品文档
│   ├── tech-design/   # 技术设计文档
│   ├── iteration/     # 迭代记录
│   └── iterations/    # 新迭代产物目录
├── AGENTS.md          # 仓库级 Agent 工作规范
├── CLAUDE.md          # Claude Code 开发指导
└── MEMORY.md          # 项目记忆
```

## 文档索引

| 目录 | 内容 |
|------|------|
| `standards/` | 长期规范：迭代流程、文档命名、Skill 使用策略 |
| `architecture/` | 当前系统架构蓝图，例如 Agent 领域模型 |
| `product-design/` | 产品需求（PRD） |
| `tech-design/` | 历史技术设计文档，后续逐步迁移到 `architecture/` |
| `iteration/` | 历史迭代记录 |
| `iterations/` | 新迭代产物目录 |

详细文档请查看 [docs/README.md](docs/README.md)。

### 快速链接

| 文档 | 说明 |
|------|------|
| [开发指南](docs/standards/DEVELOPMENT-GUIDE.md) | 环境配置、启动步骤、测试方法 |
| [API 规范](docs/tech-design/API-SPEC.md) | API 端点设计 |
| [数据库设计](docs/tech-design/DATABASE.md) | 数据模型与表结构 |
| [安全设计](docs/tech-design/SECURITY.md) | 认证、授权、限流策略 |

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
