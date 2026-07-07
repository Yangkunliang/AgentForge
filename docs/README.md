# AgentForge

**AgentForge** — 面向生产的多智能体协同框架。

**当前重心**：全栈开发自动化。

---

## 目录结构

```
docs/
├── standards/      # 长期规范：文档、迭代、Skill 使用策略
├── architecture/   # 当前系统架构蓝图
├── product-design/ # 产品文档
├── tech-design/    # 技术设计文档
├── iterations/     # 迭代记录
└── tasks/          # 任务清单
```

## 长期规范 (standards/)

| 文档 | 说明 | 状态 |
|------|------|------|
| [ITERATION-STANDARD.md](standards/ITERATION-STANDARD.md) | 迭代目录、产物命名、checklist 字段、小步提交、本地 UI/UX Skill 使用策略 | ✅ |
| [DEVELOPMENT-GUIDE.md](standards/DEVELOPMENT-GUIDE.md) | 环境配置、启动步骤、测试方法、开发规范 | ✅ |

## 当前系统架构 (architecture/)

| 文档 | 说明 | 状态 |
|------|------|------|
| [AGENT-MODEL.md](architecture/AGENT-MODEL.md) | AgentForge 产品内部的 Agent 定义、类型、能力模型、协作机制 | ✅ |

## 设计文档清单 (tech-design/)

| 文档 | 说明 | 状态 |
|------|------|------|
| [ARCHITECTURE.md](tech-design/ARCHITECTURE.md) | 整体架构、Harness 六层、消息总线、执行流程、沙箱池 | ✅ |
| [API-SPEC.md](tech-design/API-SPEC.md) | 完整 API 规范（认证、任务、Agent、Skill、Dashboard、Cost、SSE、Webhook、导出） | ✅ |
| [DATABASE.md](tech-design/DATABASE.md) | 数据库实体（9 张表）+ 记忆系统表（semantic_entries、user_memories、pgvector 全文索引） | ✅ |
| [SECURITY.md](tech-design/SECURITY.md) | 认证体系、限流、Prompt 注入防护（三类注入 + 语义检测）、Skill 沙箱分级、审计日志 | ✅ |
| [LLM-CONFIG.md](tech-design/LLM-CONFIG.md) | LLM Provider 接口、配置管理、两级 Prompt、Thinking 拆分、ReAct tool_use 循环、Cost 追踪 | ✅ |
| [FRONTEND-ARCHITECTURE.md](tech-design/FRONTEND-ARCHITECTURE.md) | Vue 3 前端架构（SSE 方案、Token 策略、权限模型、Store 同步） | ✅ |
| [RABBITMQ.md](tech-design/RABBITMQ.md) | 消息队列拓扑、Exchange/Queue 设计、消息格式、死信处理 | ✅ |
| [DEPLOYMENT.md](tech-design/DEPLOYMENT.md) | 本地开发环境、生产部署、Nginx 配置、数据库迁移 | ✅ |
| [SANDBOX-RESEARCH.md](tech-design/SANDBOX-RESEARCH.md) | 沙箱机制调研报告（Docker vs CubeSandbox 对比） | ✅ |
| [INTEGRATION-CUBESANDBOX.md](tech-design/INTEGRATION-CUBESANDBOX.md) | CubeSandbox 集成设计（E2B SDK / REST API、API 设计、分级策略） | ✅ |
| [DATA-EXPORT.md](tech-design/DATA-EXPORT.md) | 训练数据导出（JSONL）、PII 脱敏策略 | ✅ |
| [SSE-EXECUTION-VISUALIZATION.md](tech-design/SSE-EXECUTION-VISUALIZATION.md) | SSE 执行可视化方案 | ✅ |

## 产品文档 (product-design/)

| 文档 | 说明 | 状态 |
|------|------|------|
| [PRD-全栈Agent交互体验-20260623.md](product-design/PRD-全栈Agent交互体验-20260623.md) | 项目管理、意图路由、阶段感知对话、快捷动作体系、Agent Bridge | ✅ |
| [PRD-CLAW-集成能力层-20260622.md](product-design/PRD-CLAW-集成能力层-20260622.md) | CLAW 集成能力层（Skill / MCP / ClaWHub 市场） | ✅ |
| [PRD-多智能体框架-20260617.md](product-design/PRD-多智能体框架-20260617.md) | 产品定位、用户故事、核心功能、技术栈 | ✅ |

## 任务清单 (tasks/)

| 文档 | 说明 | 状态 |
|------|------|------|
| [CHECKLIST.md](tasks/CHECKLIST.md) | 实现任务清单，按 P1→P2→P3→P4 优先级排列，共 28 项 | ✅ |

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
| TASK-001 | 2026-01-20 | 项目基础设施与认证系统 | ✅ 已完成 |
| TASK-002 | 2026-06-17 | 架构设计 | ✅ 已完成 |
| TASK-003 | 2026-06-20 | Harness 核心 + RabbitMQ + SSE | ✅ 已完成 |
| TASK-004 | 2026-06-20 | Skill 管理 + Dashboard + 费用统计 + 数据导出 | ✅ 已完成 |
| TASK-005 | 2026-06-20 | 前端工作台（Vue 3 + Element Plus + SSE） | ✅ 已完成 |
| TASK-006 | 2026-06-22 | Skill 引擎（ReAct + Thinking 拆分 + Tracing） | ✅ 已完成 |
| TASK-011 | 2026-07-07 | 高级设置面板真实透传 + 技术风险修正 | ✅ 已实现，验证中 |

### TASK-002 详细信息
- **目录**：`docs/iterations/2026-06-17-architecture-design/`
- **产物**：
  - [ITER-architecture-design-20260617.md](iterations/2026-06-17-architecture-design/ITER-architecture-design-20260617.md)
- **核心功能**：Harness 六层架构、Skill 格式、技术栈决策

### TASK-003 ~ TASK-005 详细信息
以上三个 TASK 共享 `docs/iterations/2025-06-20-*` 目录，产物见各子目录的 `PRODUCT-REQUIREMENTS.md`、`TASK-CHECKLIST.md`、`TECHNICAL-DESIGN.md`。
- **核心功能**：RabbitMQ 消息总线、Harness 六层架构、SSE 流式输出、LLM Provider 抽象、Agent 基类
- Skill 管理 API、Dashboard、费用统计、数据导出
- 前端项目骨架、API 层、Pinia Store、SSE 客户端、路由守卫

### TASK-006 详细信息
- **目录**：`docs/iterations/2026-06-22-skill-engine/`
- **核心功能**：Skill 引擎 ReAct 多轮 tool_use 循环、Thinking 流式拆分、@span Tracing 自动采集

### TASK-011 详细信息
- **目录**：`docs/iterations/2026-07-07-task-011-risk-fixes/`
- **产物**：
  - [TECHNICAL-DESIGN.md](iterations/2026-07-07-task-011-risk-fixes/TECHNICAL-DESIGN.md)
- **核心功能**：高级设置状态持久化、上下文/阶段配置请求透传、system prompt 注入、沙箱配置和 API 路由前缀风险修正

## 版本号规范

- 新迭代目录：`docs/iterations/YYYY-MM-DD-topic/`
- 标准产物：`PRODUCT-REQUIREMENTS.md`、`TASK-CHECKLIST.md`、`TECHNICAL-DESIGN.md`、`TEST-PLAN.md`、`ITERATION-REVIEW.md`
- UI 相关迭代增加：`UI-DESIGN.md`
- 历史 `PRD-*`、`TASK-*`、`TEST-*`、`ITER-*` 文件保留可追溯，后续新迭代使用新命名规范
