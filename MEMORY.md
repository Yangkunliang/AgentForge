# AgentForge 项目文档索引

## 产品设计文档 (docs/product-design/)
- [PRD-全栈Agent交互体验-20260623.md](docs/product-design/PRD-全栈Agent交互体验-20260623.md) — 项目管理、意图路由、阶段感知对话、快捷动作体系、Agent Bridge 完整产品方案
- [PRD-CLAW-集成能力层-20260622.md](docs/product-design/PRD-CLAW-集成能力层-20260622.md) — CLAW 集成能力层（L1 Skill / L2 MCP / L3 ClaWHub 市场）

## 产品文档 (docs/product-design/)
- [PRD-多智能体框架-20260617.md](docs/product-design/PRD-多智能体框架-20260617.md) — 产品定位、用户故事、核心功能、技术栈

## 技术设计文档 (docs/tech-design/)
- [ARCHITECTURE.md](docs/tech-design/ARCHITECTURE.md) — Harness 六层架构、消息总线、执行流程
- [API-SPEC.md](docs/tech-design/API-SPEC.md) — 完整 API 规范（Project、Mount、Pipeline Catalog、PipelineRun、StageState、Artifact、Delivery、Evaluation、认证、任务、Agent、Skill、Dashboard、费用、SSE、Webhook、导出）
- [DATABASE.md](docs/tech-design/DATABASE.md) — 数据库实体、Project/Mount/PipelineRun/StageState/Artifact/Delivery/EvalEvent 核心闭环表、索引、关系图 + 记忆系统表（semantic_entries、user_memories、pgvector、chat_messages 全文索引）
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
- [CORE-DEV-WORKFLOW.md](docs/architecture/CORE-DEV-WORKFLOW.md) — 核心开发闭环：Project → Mount → Session → PipelineRun → StageState → Artifact → Delivery；增强阶段按 TASK-020 服务端可信交付、TASK-021 交互复盘、TASK-022 交付扩展设计、TASK-023～TASK-026 实现推进
- [AI-RUNTIME-CONVERGENCE.md](docs/architecture/AI-RUNTIME-CONVERGENCE.md) — AI Runtime 收敛主线：Project → Intent → Pipeline → Stage → Agent/Profile → Skill Runtime → Artifact → Delivery → Eval Feedback，作为 TASK-028～TASK-039 的架构基线

## 任务清单 (docs/tasks/)
- [CHECKLIST.md](docs/tasks/CHECKLIST.md) — 实现任务清单、核心开发闭环覆盖矩阵、TASK-012～TASK-026 路线图
- [TASK-012.md](docs/tasks/TASK-012.md) — 核心功能路线图与任务重排，已完成
- [TASK-013.md](docs/tasks/TASK-013.md) — Project / Mount / Artifact 数据底座，已完成
- [TASK-014.md](docs/tasks/TASK-014.md) — 项目管理页接真实数据，已完成
- [TASK-015.md](docs/tasks/TASK-015.md) — PipelineRun / StageState 阶段状态机，已完成
- [TASK-016.md](docs/tasks/TASK-016.md) — Artifact 产物归档与查看，已完成
- [TASK-017.md](docs/tasks/TASK-017.md) — 人工确认与阶段继续机制，已完成
- [TASK-018.md](docs/tasks/TASK-018.md) — Agent Bridge / 真实代码库读取，已完成
- [TASK-019.md](docs/tasks/TASK-019.md) — 写回与交付闭环，已完成
- [TASK-020.md](docs/tasks/TASK-020.md) — 服务端可信交付巩固，已完成
- [TASK-021.md](docs/tasks/TASK-021.md) — 核心交互设计复盘与关键入口优化，已完成
- [TASK-022.md](docs/tasks/TASK-022.md) — 交付能力扩展设计与实现，已完成
- [TASK-023.md](docs/tasks/TASK-023.md) — GitHub OAuth Mount 授权底座，已完成
- [TASK-024.md](docs/tasks/TASK-024.md) — GitHub PR Delivery，已完成
- [TASK-025.md](docs/tasks/TASK-025.md) — zip Delivery Package，已完成
- [TASK-026.md](docs/tasks/TASK-026.md) — Upload Mount 上下文兜底，已完成

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
- [2026-07-08-core-strengthening/](docs/iterations/2026-07-08-core-strengthening/) — TASK-020～TASK-026 核心能力增强排期
  - [PRODUCT-REQUIREMENTS.md](docs/iterations/2026-07-08-core-strengthening/PRODUCT-REQUIREMENTS.md) — 可信写回、下一步动作清楚、多交付方式
  - [TASK-CHECKLIST.md](docs/iterations/2026-07-08-core-strengthening/TASK-CHECKLIST.md) — TASK-020～TASK-026 优先级、依赖和防遗忘机制
  - [TECHNICAL-DESIGN.md](docs/iterations/2026-07-08-core-strengthening/TECHNICAL-DESIGN.md) — Delivery fingerprint、一致性校验、失败报告、审计日志、GitHub PR、zip、upload 扩展边界
  - [UI-REVIEW.md](docs/iterations/2026-07-08-core-strengthening/UI-REVIEW.md) — TASK-021 核心交互入口复盘、设计约束和 E2E 验收覆盖
  - [TEST-PLAN.md](docs/iterations/2026-07-08-core-strengthening/TEST-PLAN.md) — 服务端、UI、交付扩展验证矩阵
  - [ITERATION-REVIEW.md](docs/iterations/2026-07-08-core-strengthening/ITERATION-REVIEW.md) — TASK-020～TASK-025 完成内容、风险修正和验证结果
- [2026-07-09-ai-architecture-convergence/](docs/iterations/2026-07-09-ai-architecture-convergence/) — TASK-027～TASK-034 AI Runtime 收敛，推荐从 `ITERATION-REVIEW.md` 和 `docs/architecture/AI-RUNTIME-CONVERGENCE.md` 阅读当前状态
  - [PRODUCT-REQUIREMENTS.md](docs/iterations/2026-07-09-ai-architecture-convergence/PRODUCT-REQUIREMENTS.md) — AI Runtime 收敛的用户故事、范围和分阶段计划
  - [TASK-CHECKLIST.md](docs/iterations/2026-07-09-ai-architecture-convergence/TASK-CHECKLIST.md) — TASK-027～TASK-034 优先级、依赖和完成状态
  - [TECHNICAL-DESIGN.md](docs/iterations/2026-07-09-ai-architecture-convergence/TECHNICAL-DESIGN.md) — Pipeline Catalog、AgentResolver、ModelRouter、SkillRuntime、GovernancePolicy 和 EvalEvent 设计边界
  - [TEST-PLAN.md](docs/iterations/2026-07-09-ai-architecture-convergence/TEST-PLAN.md) — AI Runtime 收敛测试矩阵
  - [ITERATION-REVIEW.md](docs/iterations/2026-07-09-ai-architecture-convergence/ITERATION-REVIEW.md) — TASK-027～TASK-034 完成情况、验证结果和遗留风险
- [2026-07-13-dashboard-skill-authorization-metrics/](docs/iterations/2026-07-13-dashboard-skill-authorization-metrics/) — TASK-042 Dashboard 高风险 Skill 授权指标，将 TASK-041 summary 聚合接入 Dashboard API 和页面

## 文档体系
- [docs/README.md](docs/README.md) — 文档目录结构、迭代链条、版本号规范

## 当前实现进度

- TASK-015 已完成：后端 `PipelineRun` / `PipelineStageState` 模型、`011_pipeline_run_stage_state.py` 迁移、pipeline intent 配置表、阶段状态 API、StageRuntime 与 SkillExecutionEngine 连接、pipeline/stage SSE 事件已落地。
- 前端已新增 `pipelineRunsApi`、`usePipelineStore`，Chat 进入已有 Session 或首次发送消息后会拉取当前 PipelineRun；StagePreview 在有后端 run 时以 StageState 为唯一状态源，optional skip/restore 会落库。
- TASK-016 已完成：`src/agent_forge/artifacts/service.py` 负责阶段到 Artifact 类型映射；StageRuntime 阶段完成后创建 Artifact 并发 `artifact_created` SSE；`GET /sessions/{id}/messages` 会回带关联 artifacts；前端新增 `artifactsApi`、`useArtifactStore`、`ArtifactCard`、`/artifacts/:artifactId` Viewer，Project 页展示最近产物，Artifact 可作为 `context_files[type=artifact]` 加入下一轮上下文。
- TASK-017 已完成：`PipelineStageState` 新增确认动作、反馈和处理时间字段；确认阶段完成后进入 `waiting_confirmation` 并发 `confirm_required`；`POST /pipeline-runs/{run_id}/stages/{stage_id}/confirm` 支持 approve/revise/cancel；StageRuntime 等待确认时停止调用 SkillExecutionEngine，revise 反馈会注入下一次同阶段执行；Chat ConfirmCard 已接真实 API 和 Artifact。
- TASK-018 已完成：新增 `agentforge mount <path>` CLI、Bridge 状态和文件列表/读取 API、授权 root 内路径校验、敏感文件拒绝、ContextPicker 挂载文件选择，以及 Chat `context_files[type=file].mount_id` 真实内容注入 SkillExecutionEngine。
- TASK-019 已完成：新增 `agent_forge.delivery`、Artifact delivery 字段、diff preview、`confirm_write` 写回 connected local Mount、写前 `.agentforge.bak` 备份、Delivery report 和 Markdown 导出；Artifact Viewer 已接交付面板。
- TASK-020 已完成：Delivery preview/apply 一致性校验、失败报告、`AuditLog.resource=artifact_delivery` 审计、默认不预热远程 E2B 沙箱。
- TASK-021 已完成：Project 页按 Mount、PipelineRun、Artifact 聚合下一步动作；Chat 空状态展示当前项目和代码库连接状态；StagePreview 展示当前阶段摘要；ConfirmCard 增加“查看产物并交付”；ArtifactCard 展示交付状态。
- TASK-022 已完成：GitHub OAuth Mount、GitHub PR Delivery、zip Delivery、Upload Mount 的授权边界、数据流、失败状态和审计点已写入技术设计，并拆出 TASK-023～TASK-026。
- TASK-023 已完成：GitHub OAuth start/callback、`oauth_credentials`/`oauth_states`、服务端加密凭据、connected GitHub Mount 创建、删除撤销 credential、Project 创建向导 OAuth 授权入口已落地；callback 通过一次性 state 找回用户和项目，不依赖浏览器重定向携带 JWT header。
- TASK-024 已完成：GitHub PR Delivery preview/apply API、`expected_base_sha` 二次校验、branch/commit/PR 创建、失败报告、`delivery.github.*` 审计事件和 Artifact Viewer GitHub PR 模式已落地。
- TASK-025 已完成：zip Delivery preview/apply/download API、deterministic zip sha256、manifest/report、下载权限隔离、过期清理、`delivery.zip.*` 审计事件和 Artifact Viewer zip 包模式已落地。
- TASK-026 已完成：Upload Mount multipart 上传 API、manifest 范围读取、Bridge/Chat 上下文读取、路径/数量/大小/扩展名限制、`upload_mount.*` 审计、Project 创建向导上传模式和 ContextPicker upload 文件源已落地。
- TASK-027 已完成：新增 AI Runtime 收敛架构基线，明确 Project → Intent → Pipeline → Stage → Agent/Profile → Skill Runtime → Artifact → Delivery → Eval Feedback 主链路、当前代码映射、目标运行时契约和 TASK-028～TASK-039 迁移边界。
- TASK-028 已完成：新增 `src/agent_forge/pipeline/catalog.py` 和 `/api/v1/pipeline/catalog`，将 intent -> StageDefinition 收敛为后端唯一事实源；StageRuntime、PipelineService 与前端 Pipeline Store 已消费 Catalog，阶段定义包含确认策略、输出产物类型、默认 Agent selector、ModelRoute key 和 SkillPolicy key。
- TASK-029 已完成：新增 `src/agent_forge/agents/resolver.py`，按用户覆盖、项目默认、StageDefinition.default_agent_selector、系统默认解析 AgentProfile；StageRuntime 会把 `agent_profile_id/name/source` 写入 `PipelineStageState`，并将 AgentProfile 注入 SkillExecutionEngine 上下文；新增 `/api/v1/agents/runtime/candidates` 返回运行时 active Agent 候选。
- TASK-030 已完成：新增 `src/agent_forge/llm/router.py`、`src/agent_forge/models/llm.py` 和 `016_llm_model_routes.py`；LLM 设置页和 `/api/v1/llm/*` 支持 Provider / Model / Credential / Route，Credential 加密存储且 API 只返回 masked 信息；StageRuntime 会解析 ModelRoute、写入 StageState 模型追踪字段并将非敏感 route 上下注入 SkillExecutionEngine。
- TASK-031 已完成：新增 `src/agent_forge/skills/runtime_spec.py`、`src/agent_forge/skills/policy.py` 和 `017_skill_runtime_policy.py`；Skill Manifest 支持 `agentforge-skill.yaml` 优先、`skill.md` 兼容，`/api/v1/skills/import/preview` 与 `/api/v1/skills/import/install` 会展示来源、工具、权限、风险和确认要求；安装后 Skill/SkillInstall 记录 manifest_hash、permissions、runtime_spec 和 preview，SkillRegistry 注册 runtime spec，SkillDispatcher 调用前执行权限校验并写入 `skill.invoke.*` 审计和 `skill_eval` 事件。
- TASK-032 已完成：新增 `src/agent_forge/governance/policy.py` 和 `018_governance_confirmation_context.py`；`PipelineStageState` 记录确认类型、原因、影响范围和审计 payload；Pipeline 阶段确认、Delivery 未确认拒绝和高风险 Skill 调用拒绝均写入 `governance_decision`；ConfirmCard 渲染服务端策略生成的确认原因与影响范围。
- TASK-033 已完成：新增 `src/agent_forge/evaluation/service.py`、`src/agent_forge/models/evaluation.py` 和 `019_eval_events.py`；StageRuntime、SkillDispatcher、Pipeline 确认和 Delivery 会以非阻塞方式写入 `EvalEvent`；新增 `/api/v1/evaluation/summary`、Dashboard evaluation 指标和 `eval_events` / `evaluation` JSONL 导出类型。
- TASK-034 已完成：更新 Agent 模型、核心开发闭环、AI Runtime 主线、ARCHITECTURE、LLM-CONFIG、API-SPEC、DATABASE、SECURITY、DATA-EXPORT、docs README、MEMORY、CLAUDE，并新增 AI Runtime 迭代复盘；当前推荐阅读路径是 `docs/README.md` → `docs/architecture/AI-RUNTIME-CONVERGENCE.md` → `docs/iterations/2026-07-09-ai-architecture-convergence/ITERATION-REVIEW.md`。
- TASK-035 已完成：新增 `filter_tool_defs_for_runtime()` 和 StageSkillPolicy 过滤报告；AgentResolver 从 `agent_skills` 生成 `AgentProfile.allowed_skill_names`；StageRuntime 调用 SkillExecutionEngine 前按阶段策略、Agent allowlist 和 SkillRuntimeSpec permissions 过滤 tools，SkillDispatcher 权限校验继续作为第二道防线。
- TASK-036 已完成：`MCPServerConfig` 支持 permissions 声明，未声明权限默认按 `credential` 高风险处理；MCP 注册到 SkillRegistry 时生成 `source_type=mcp`、`executor_kind=mcp` 的 RuntimeSpec，并复用 StageSkillPolicy 过滤高风险 MCP tool。
- TASK-037 已完成：新增 `external_side_effect` 高风险权限；内置 Skill 注册时生成 `source_type=builtin` 的 RuntimeSpec；默认 StageSkillPolicy 只暴露 `web_search` 和 `get_weather`，过滤 `http_request`、`update_profile`、`code_executor`。
- TASK-038 已完成：StageRuntime 支持 `advanced_context.skill_authorization` 阶段级临时授权；`filter_tool_defs_for_runtime()` 可按 `authorized_skill_names` / `authorized_permissions` 临时放行高风险 Skill，但不会绕过 AgentSkill allowlist，过滤报告会记录授权范围。
- TASK-039 已完成：Chat API 支持一次性 `skill_authorization` payload；StageRuntime 会对可授权的高风险 Skill 发出 `skill_authorization_required` SSE；前端新增 `SkillAuthorizationCard`，用户确认后以同一条消息和临时授权 payload 重试当前阶段。
- TASK-040 已完成：`SkillToolFilterReport` 记录 `authorized_tools`；StageRuntime 将 `skill_authorization_required` 和 `skill_authorization_granted` 写入 EvalEvent，后续可按阶段、Skill、Tool 和权限分析高风险授权频率。
- TASK-041 已完成：Evaluation summary 新增 `skill_authorizations` 聚合块，按 Skill 和 permission 输出 required、granted、grant_rate，便于后续 Dashboard 和策略优化消费。
- TASK-042 已完成：Dashboard evaluation 返回 `skill_authorizations`，前端 Dashboard 展示高风险 Skill 授权请求、已授权、通过率，以及按 Skill / permission 的前 3 项排行。

---

## 开发约定

- 实现前先阅读对应设计文档，以文档为准
- 每完成 `CHECKLIST.md` 中一项，立即勾选并单独 commit
- 本地启动顺序：`docker compose up -d` → `alembic upgrade head` → 后端 → 前端（详见 `DEPLOYMENT.md`）
- 前端 API 类型通过 `npm run gen:types` 自动生成，禁止手写
