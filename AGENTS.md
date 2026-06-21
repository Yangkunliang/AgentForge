# AgentForge 仓库级 Agent 工作规范

## 1. 项目定位

AgentForge 是面向生产的多智能体协同框架。当前阶段以架构设计和文档规范为先，开发执行在架构 checklist 明确后推进。

## 2. 工作原则

- 架构先行：先明确范围、模块边界、数据流、接口和验收标准，再进入实现。
- 小步迭代：每次迭代先建立任务 checklist，按模块和优先级排序。
- 小步提交：完成 1 个 checklist item 后，立即勾选完成并单独 commit 一次。
- 文档同步：目录、规范、架构和迭代产物发生变化时，同步更新 `docs/README.md` 与 `MEMORY.md`。
- 避免混淆：根目录 `AGENTS.md` 只放仓库级 Agent 工作规范；AgentForge 产品中的 Agent 领域模型放在 `docs/architecture/AGENT-MODEL.md`。

## 3. 文档目录约定

- `docs/standards/`：长期规范，例如文档命名、迭代流程、提交节奏、Skill 使用策略。
- `docs/architecture/`：当前系统架构蓝图，例如 Agent 模型、Harness、API、数据库、安全、前端架构。
- `docs/iterations/`：每次迭代生成的过程文档，按日期和主题建目录。
- `docs/product-design/`、`docs/tech-design/`、`docs/iteration/`：历史文档目录，迁移时应保持索引可追溯。

## 4. 迭代产物命名

新迭代目录建议使用以下文件名：

```text
docs/iterations/YYYY-MM-DD-topic/
├── PRODUCT-REQUIREMENTS.md
├── TASK-CHECKLIST.md
├── TECHNICAL-DESIGN.md
├── UI-DESIGN.md
├── TEST-PLAN.md
└── ITERATION-REVIEW.md
```

`UI-DESIGN.md` 仅在涉及 UI/UX 时创建。

## 5. 本地 UI/UX Skill 使用约束

前端 UI/UX 设计类任务允许使用本地已安装的 `ui-ux-pro-max` skill：

```text
~/.claude/skills/ui-ux-pro-max
```

使用边界：

- 仅作为 advisory skill 使用。
- 仅用于 UI design、UX review、design system、frontend visual spec 等任务。
- 输出必须沉淀到 `UI-DESIGN.md` 或 `UI-REVIEW.md`。
- 不得用于后端架构、数据库、安全、部署、Agent 编排或核心领域模型决策。
- 该 skill 属于开发过程辅助能力，不默认进入 AgentForge 产品运行时的 SkillRegistry。

## 6. 验证要求

文档类变更至少检查：

- 链接和路径是否准确。
- 规范与目录结构是否一致。
- 是否存在同名但语义不同的文档。
- 是否更新了相关索引。

## 7. 架构变更自动同步

当对话中产生**架构级别**变更时，Agent 应主动同步更新架构文档，无需用户额外指示。

**触发条件**（满足任一即触发）：

- 新增、删除或重命名模块/子系统
- 模块间接口或数据流变更
- 数据模型（表结构、核心实体）调整
- 技术选型变更（框架、中间件、数据库、协议等）
- 部署架构或基础设施变更

**不触发**：bug 修复、小功能增强、样式调整、依赖升级等非架构变更。

**同步目标**：

- `docs/architecture/` 下相关架构文档
- `MEMORY.md`（若涉及架构概要变更）
- `CLAUDE.md`（若涉及架构概要或技术栈变更）

**执行节奏**：在变更完成后立即同步，与代码变更在同一次 commit 中提交。
