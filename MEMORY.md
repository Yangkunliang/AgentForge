# AgentForge 项目文档索引

## 产品设计文档 (docs/product-design/)
- [PRD-全栈Agent交互体验-20260623.md](docs/product-design/PRD-全栈Agent交互体验-20260623.md) — 项目管理、意图路由、阶段感知对话、快捷动作体系、Agent Bridge 完整产品方案
- [PRD-CLAW-集成能力层-20260622.md](docs/product-design/PRD-CLAW-集成能力层-20260622.md) — CLAW 集成能力层（L1 Skill / L2 MCP / L3 ClaWHub 市场）

## 产品文档 (docs/product-design/)
- [PRD-多智能体框架-20260617.md](docs/product-design/PRD-多智能体框架-20260617.md) — 产品定位、用户故事、核心功能、技术栈

## 技术设计文档 (docs/tech-design/)
- [ARCHITECTURE.md](docs/tech-design/ARCHITECTURE.md) — Harness 六层架构、消息总线、执行流程
- [API-SPEC.md](docs/tech-design/API-SPEC.md) — 完整 API 规范（Project、Mount、PipelineRun、StageState、Artifact、认证、任务、Agent、Skill、Dashboard、费用、SSE、Webhook、导出）
- [DATABASE.md](docs/tech-design/DATABASE.md) — 数据库实体、Project/Mount/PipelineRun/StageState/Artifact 核心闭环表、索引、关系图 + 记忆系统表（semantic_entries、user_memories、pgvector、chat_messages 全文索引）
- [SECURITY.md](docs/tech-design/SECURITY.md) — 认证体系、限流、Prompt 注入防护（三类注入 + 语义检测 + tool_call 分级）、Skill 沙箱分级、审计日志
- [SANDBOX-RESEARCH.md](docs/tech-design/SANDBOX-RESEARCH.md) — 沙箱机制技术调研报告（方案一 Docker vs 方案二 CubeSandbox，含对比表格与选型依据）
- [INTEGRATION-CUBESANDBOX.md](docs/tech-design/INTEGRATION-CUBESANDBOX.md) — CubeSandbox 集成详细设计（抽象层、E2B SDK / REST API 两种对接路径、API 设计、分级策略、实施计划）
- [LLM-CONFIG.md](docs/tech-design/LLM-CONFIG.md) — LiteLLM 配置、模型路由、Fallback、Cost 追踪
- [DATA-EXPORT.md](docs/tech-design/DATA-EXPORT.md) — 训练数据导出、PII 脱敏策略
- [FRONTEND-ARCHITECTURE.md](docs/tech-design/FRONTEND-ARCHITECTURE.md) — Vue 3 前端架构（Project Store、SSE 方案、Token 策略、权限模型、Store 同步）
- [RABBITMQ.md](docs/tech-design/RABBITMQ.md) — 消息队列拓扑、Exchange/Queue 设计、消息格式、死信处理
- [DEPLOYMENT.md](docs/tech-design/DEPLOYMENT.md) — 本地开发环境、生产部署、Nginx 配置、数据库迁移

## 架构蓝图 (docs/architecture/)
- [AGENT-MODEL.md](docs/architecture/AGENT-MODEL.md) — AgentForge 产品内部的 Agent 定义、类型、能力模型、协作机制
- [CORE-DEV-WORKFLOW.md](docs/architecture/CORE-DEV-WORKFLOW.md) — 核心开发闭环：Project → Mount → Session → PipelineRun → StageState → Artifact → Delivery

## 任务清单 (docs/tasks/)
- [CHECKLIST.md](docs/tasks/CHECKLIST.md) — 实现任务清单、核心开发闭环覆盖矩阵、TASK-012～TASK-019 后续路线图
- [TASK-012.md](docs/tasks/TASK-012.md) — 核心功能路线图与任务重排，已完成
- [TASK-013.md](docs/tasks/TASK-013.md) — Project / Mount / Artifact 数据底座，已完成
- [TASK-014.md](docs/tasks/TASK-014.md) — 项目管理页接真实数据，已完成
- [TASK-015.md](docs/tasks/TASK-015.md) — PipelineRun / StageState 阶段状态机，已完成
- [TASK-016.md](docs/tasks/TASK-016.md) — Artifact 产物归档与查看，已完成
- [TASK-017.md](docs/tasks/TASK-017.md) — 人工确认与阶段继续机制，已完成
- [TASK-018.md](docs/tasks/TASK-018.md) — Agent Bridge / 真实代码库读取，已完成
- [TASK-019.md](docs/tasks/TASK-019.md) — 写回与交付闭环，todo

## 迭代记录 (docs/iterations/)
- [2026-06-17-architecture-design/](docs/iterations/2026-06-17-architecture-design/) — 架构设计迭代记录
  - [ITER-architecture-design-20260617.md](docs/iterations/2026-06-17-architecture-design/ITER-architecture-design-20260617.md) — Harness 六层架构、Skill 格式、技术栈决策
- [2025-06-20-task-agent-management-api/](docs/iterations/2025-06-20-task-agent-management-api/) — TASK-002 任务管理与 Agent 管理 API
  - [PRODUCT-REQUIREMENTS.md](docs/iterations/2025-06-20-task-agent-management-api/PRODUCT-REQUIREMENTS.md) — 产品需求文档
  - [TASK-CHECKLIST.md](docs/iterations/2025-06-20-task-agent-management-api/TASK-CHECKLIST.md) — 任务清单和问题解决记录
  - [TECHNICAL-DESIGN.md](docs/iterations/2025-06-20-task-agent-management-api/TECHNICAL-DESIGN.md) — 技术设计文档
- [2025-06-20-harness-core-rabbitmq-sse/](docs/iterations/2025-06-20-harness-core-rabbitmq-sse/) — TASK-003 Harness 核心 + RabbitMQ + SSE
  - [PRODUCT-REQUIREMENTS.md](docs/iterations/2025-06-20-harness-core-rabbitmq-sse/PRODUCT-REQUIREMENTS.md) — 产品需求文档
  - [TASK-CHECKLIST.md](docs/iterations/2025-06-20-harness-core-rabbitmq-sse/TASK-CHECKLIST.md) — 任务清单
  - [TECHNICAL-DESIGN.md](docs/iterations/2025-06-20-harness-core-rabbitmq-sse/TECHNICAL-DESIGN.md) — 技术设计文档
- [2025-06-20-frontend-workbench/](docs/iterations/2025-06-20-frontend-workbench/) — 前端工作台迭代
- [2025-06-20-skill-dashboard-cost-exports/](docs/iterations/2025-06-20-skill-dashboard-cost-exports/) — Skill 面板与成本导出
- [2026-06-22-skill-engine/](docs/iterations/2026-06-22-skill-engine/) — Skill 引擎迭代
- [2026-07-07-task-009-sse-validation/](docs/iterations/2026-07-07-task-009-sse-validation/) — TASK-009 SSE 执行过程可视化联调验证
  - [TECHNICAL-DESIGN.md](docs/iterations/2026-07-07-task-009-sse-validation/TECHNICAL-DESIGN.md) — 执行步骤收集器、code_executor 单卡展示、stdout/stderr 补全、失败/超时状态风险修正
  - [TEST-PLAN.md](docs/iterations/2026-07-07-task-009-sse-validation/TEST-PLAN.md) — thinking、tool_call、code_executor、timeout、多步骤顺序、浏览器视觉状态和移动端溢出的自动化验收计划
  - [ITERATION-REVIEW.md](docs/iterations/2026-07-07-task-009-sse-validation/ITERATION-REVIEW.md) — TASK-009 浏览器 E2E 验收结论、验证命令和剩余边界
- [2026-07-07-task-011-risk-fixes/](docs/iterations/2026-07-07-task-011-risk-fixes/) — TASK-011 高级设置真实透传与技术风险修正
  - [TECHNICAL-DESIGN.md](docs/iterations/2026-07-07-task-011-risk-fixes/TECHNICAL-DESIGN.md) — intent/context/stage 透传、system prompt 注入、沙箱配置、API 路由前缀、依赖锁、SQLite 测试方言与全量 pytest 风险修正
- [2026-07-08-core-dev-workflow/](docs/iterations/2026-07-08-core-dev-workflow/) — TASK-012 核心开发闭环路线图与任务重排
  - [PRODUCT-REQUIREMENTS.md](docs/iterations/2026-07-08-core-dev-workflow/PRODUCT-REQUIREMENTS.md) — 核心闭环用户故事 CDW-01～CDW-07
  - [TASK-CHECKLIST.md](docs/iterations/2026-07-08-core-dev-workflow/TASK-CHECKLIST.md) — TASK-012～TASK-019 任务索引与防遗忘机制
  - [TECHNICAL-DESIGN.md](docs/iterations/2026-07-08-core-dev-workflow/TECHNICAL-DESIGN.md) — ProjectService、SessionService、PipelineService、StageRuntime、ArtifactService、DeliveryService 设计边界
  - [TEST-PLAN.md](docs/iterations/2026-07-08-core-dev-workflow/TEST-PLAN.md) — 分阶段验收矩阵
  - [ITERATION-REVIEW.md](docs/iterations/2026-07-08-core-dev-workflow/ITERATION-REVIEW.md) — TASK-012 决策和后续提醒

## 文档体系
- [docs/README.md](docs/README.md) — 文档目录结构、迭代链条、版本号规范

## 当前实现进度

- TASK-015 已完成：后端 `PipelineRun` / `PipelineStageState` 模型、`011_pipeline_run_stage_state.py` 迁移、pipeline intent 配置表、阶段状态 API、StageRuntime 与 SkillExecutionEngine 连接、pipeline/stage SSE 事件已落地。
- 前端已新增 `pipelineRunsApi`、`usePipelineStore`，Chat 进入已有 Session 或首次发送消息后会拉取当前 PipelineRun；StagePreview 在有后端 run 时以 StageState 为唯一状态源，optional skip/restore 会落库。
- TASK-016 已完成：`src/agent_forge/artifacts/service.py` 负责阶段到 Artifact 类型映射；StageRuntime 阶段完成后创建 Artifact 并发 `artifact_created` SSE；`GET /sessions/{id}/messages` 会回带关联 artifacts；前端新增 `artifactsApi`、`useArtifactStore`、`ArtifactCard`、`/artifacts/:artifactId` Viewer，Project 页展示最近产物，Artifact 可作为 `context_files[type=artifact]` 加入下一轮上下文。
- TASK-017 已完成：`PipelineStageState` 新增确认动作、反馈和处理时间字段；确认阶段完成后进入 `waiting_confirmation` 并发 `confirm_required`；`POST /pipeline-runs/{run_id}/stages/{stage_id}/confirm` 支持 approve/revise/cancel；StageRuntime 等待确认时停止调用 SkillExecutionEngine，revise 反馈会注入下一次同阶段执行；Chat ConfirmCard 已接真实 API 和 Artifact。
- TASK-018 已完成：新增 `agentforge mount <path>` CLI、Bridge 状态和文件列表/读取 API、授权 root 内路径校验、敏感文件拒绝、ContextPicker 挂载文件选择，以及 Chat `context_files[type=file].mount_id` 真实内容注入 SkillExecutionEngine。
- 下一步保持 TASK-019：写回与交付闭环仍未完成，不要提前声称 Agent 已能生成 diff 或写回用户本地项目。

---

## 开发约定

- 实现前先阅读对应设计文档，以文档为准
- 每完成 `CHECKLIST.md` 中一项，立即勾选并单独 commit
- 本地启动顺序：`docker compose up -d` → `alembic upgrade head` → 后端 → 前端（详见 `DEPLOYMENT.md`）
- 前端 API 类型通过 `npm run gen:types` 自动生成，禁止手写
