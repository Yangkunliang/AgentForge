# AgentForge

**AgentForge** — 面向生产的多智能体协同框架。

**当前重心**：全栈开发自动化。

---

## 目录结构

```
docs/
├── standards/      # 长期规范：文档、迭代、Skill 使用策略
├── architecture/   # 当前系统架构蓝图
├── product-design/   # 产品文档
├── tech-design/   # 技术设计文档
├── iteration/     # 迭代记录
└── iterations/    # 新迭代产物目录
```

## 长期规范 (standards/)

| 文档 | 说明 | 状态 |
|------|------|------|
| ITERATION-STANDARD.md | 迭代目录、产物命名、checklist 字段、小步提交、本地 UI/UX Skill 使用策略 | ✅ |
| DEVELOPMENT-GUIDE.md | 环境配置、启动步骤、测试方法、开发规范 | ✅ |

## 当前系统架构 (architecture/)

| 文档 | 说明 | 状态 |
|------|------|------|
| AGENT-MODEL.md | AgentForge 产品内部的 Agent 定义、类型、能力模型、协作机制 | ✅ |

## 设计文档清单 (tech-design/)

| 文档 | 说明 | 状态 |
|------|------|------|
| ARCHITECTURE.md | 整体架构、六层 Harness、执行流程 | ✅ |
| DATABASE.md | 数据库实体、索引、关系图 | ✅ |
| API-SPEC.md | 完整 API 规范（含注册、Dashboard、反馈、费用、Skill 安装进度） | ✅ |
| SECURITY.md | 认证、限流、沙箱、Secrets 管理 | ✅ |
| LLM-CONFIG.md | LLM Provider、模型路由、Cost 追踪 | ✅ |
| DATA-EXPORT.md | 训练数据导出、脱敏策略 | ✅ |
| FRONTEND-ARCHITECTURE.md | 前端架构（含 SSE 方案、Token 策略、权限模型、Store 同步） | ✅ |
| RABBITMQ.md | 消息队列拓扑、Exchange/Queue 设计、消息格式、死信处理 | ✅ |
| DEPLOYMENT.md | 本地开发环境、生产部署、Nginx 配置、数据库迁移 | ✅ |

## 迭代链条

每个功能迭代遵循完整链条：

1. **PRODUCT-REQUIREMENTS.md** → 产品需求（做什么）
2. **TASK-CHECKLIST.md** → 任务拆解、优先级、验收标准
3. **TECHNICAL-DESIGN.md** → 技术方案（怎么实现）
4. **UI-DESIGN.md** → UI/UX 设计（仅 UI 相关迭代需要）
5. **TEST-PLAN.md** → 测试与验收方案
6. **ITERATION-REVIEW.md** → 迭代总结（学到了什么）

## 迭代历史

| 迭代 | 日期 | 主题 | 状态 |
|------|------|------|------|
| TASK-001 | 2025-06-20 | 项目基础设施与认证系统 | ✅ 已完成 |
| TASK-002 | 2025-06-20 | 任务管理与 Agent 管理 API | ✅ 已完成 |
| TASK-003 | 2025-06-20 | Harness 核心 + RabbitMQ + SSE | ✅ 已完成 |
| TASK-004 | 2025-06-20 | Skill 管理 + Dashboard + 费用统计 + 数据导出 | ✅ 已完成 |
| TASK-005 | 2025-06-20 | 前端工作台（Vue 3 + Element Plus + SSE） | ✅ 已完成 |

### TASK-002 详细信息
- **目录**：`docs/iterations/2025-06-20-task-agent-management-api/`
- **产物**：
  - [PRODUCT-REQUIREMENTS.md](iterations/2025-06-20-task-agent-management-api/PRODUCT-REQUIREMENTS.md)
  - [TASK-CHECKLIST.md](iterations/2025-06-20-task-agent-management-api/TASK-CHECKLIST.md)
  - [TECHNICAL-DESIGN.md](iterations/2025-06-20-task-agent-management-api/TECHNICAL-DESIGN.md)
- **核心功能**：
  - 任务管理 API（创建、查询、取消、反馈）
  - Agent 管理 API（CRUD 操作）
  - 权限控制和认证
  - 完整的单元测试覆盖

### TASK-003 详细信息
- **目录**：`docs/iterations/2025-06-20-harness-core-rabbitmq-sse/`
- **产物**：
  - [PRODUCT-REQUIREMENTS.md](iterations/2025-06-20-harness-core-rabbitmq-sse/PRODUCT-REQUIREMENTS.md)
  - [TASK-CHECKLIST.md](iterations/2025-06-20-harness-core-rabbitmq-sse/TASK-CHECKLIST.md)
  - [TECHNICAL-DESIGN.md](iterations/2025-06-20-harness-core-rabbitmq-sse/TECHNICAL-DESIGN.md)
- **核心功能**：
  - RabbitMQ 消息总线（Exchange/Queue 拓扑）
  - Harness 六层架构（Validator、Router、Registry、Governance、Executor、Memory）
  - SSE 流式输出（10 种事件类型）
  - LLM Provider 抽象层（LiteLLM、模型路由、Cost 追踪）
  - Agent 基类和内置 Agent（Coder、Reviewer、Researcher）

### TASK-004 详细信息
- **目录**：`docs/iterations/2025-06-20-skill-dashboard-cost-exports/`
- **产物**：
  - [PRODUCT-REQUIREMENTS.md](iterations/2025-06-20-skill-dashboard-cost-exports/PRODUCT-REQUIREMENTS.md)
  - [TASK-CHECKLIST.md](iterations/2025-06-20-skill-dashboard-cost-exports/TASK-CHECKLIST.md)
  - [TECHNICAL-DESIGN.md](iterations/2025-06-20-skill-dashboard-cost-exports/TECHNICAL-DESIGN.md)
- **核心功能**：
  - Skill 管理 API（安装、卸载、进度查询）
  - Dashboard API（任务统计、Agent 状态、费用趋势）
  - 费用统计 API（每日费用、模型成本分布）
  - 数据导出 API（JSONL 格式、三级脱敏策略）

### TASK-005 详细信息
- **目录**：`docs/iterations/2025-06-20-frontend-workbench/`
- **产物**：
  - [PRODUCT-REQUIREMENTS.md](iterations/2025-06-20-frontend-workbench/PRODUCT-REQUIREMENTS.md)
  - [TASK-CHECKLIST.md](iterations/2025-06-20-frontend-workbench/TASK-CHECKLIST.md)
  - [TECHNICAL-DESIGN.md](iterations/2025-06-20-frontend-workbench/TECHNICAL-DESIGN.md)
- **核心功能**：
  - 前端项目骨架（Vite + Vue 3 + TypeScript + Element Plus + Pinia）
  - API 层（Axios 实例、模块化 API、类型生成脚本）
  - 状态管理（auth、task、agent、skill、app stores）
  - SSE 客户端（fetch + ReadableStream、指数退避重连）
  - 页面组件（Login、Register、Dashboard、Task、Agent、Skill、Export）
  - 路由守卫和权限控制

## 版本号规范

- 新迭代目录：`docs/iterations/YYYY-MM-DD-topic/`
- 标准产物：`PRODUCT-REQUIREMENTS.md`、`TASK-CHECKLIST.md`、`TECHNICAL-DESIGN.md`、`TEST-PLAN.md`、`ITERATION-REVIEW.md`
- UI 相关迭代增加：`UI-DESIGN.md`
- 历史 `PRD-*`、`TASK-*`、`TEST-*`、`ITER-*` 文件保留可追溯，后续新迭代使用新命名规范
