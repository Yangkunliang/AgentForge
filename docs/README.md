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
| [CORE-DEV-WORKFLOW.md](architecture/CORE-DEV-WORKFLOW.md) | AgentForge 面向全栈开发工程师的核心开发闭环：Project → Mount → Session → PipelineRun → StageState → Artifact → Delivery | ✅ |
| [AI-RUNTIME-CONVERGENCE.md](architecture/AI-RUNTIME-CONVERGENCE.md) | AI Runtime 收敛主线：Project → Intent → Pipeline → Stage → Agent/Profile → Skill Runtime → Artifact → Delivery → Eval Feedback | ✅ |

## 设计文档清单 (tech-design/)

| 文档 | 说明 | 状态 |
|------|------|------|
| [ARCHITECTURE.md](tech-design/ARCHITECTURE.md) | 整体架构、Harness 六层、消息总线、执行流程、沙箱池 | ✅ |
| [API-SPEC.md](tech-design/API-SPEC.md) | 完整 API 规范（Project、Mount、Pipeline Catalog、PipelineRun、StageState、Artifact、Delivery、Evaluation、认证、任务、Agent、Skill、Dashboard、Cost、SSE、Webhook、导出） | ✅ |
| [DATABASE.md](tech-design/DATABASE.md) | 数据库实体、Project/Mount/PipelineRun/StageState/Artifact/Delivery/EvalEvent 核心闭环表 + 记忆系统表（semantic_entries、user_memories、pgvector 全文索引） | ✅ |
| [SECURITY.md](tech-design/SECURITY.md) | 认证体系、限流、Prompt 注入防护（三类注入 + 语义检测）、Skill 沙箱分级、审计日志 | ✅ |
| [LLM-CONFIG.md](tech-design/LLM-CONFIG.md) | LLM Provider 接口、配置管理、两级 Prompt、Thinking 拆分、ReAct tool_use 循环、Cost 追踪 | ✅ |
| [FRONTEND-ARCHITECTURE.md](tech-design/FRONTEND-ARCHITECTURE.md) | Vue 3 前端架构（Project Store、SSE 方案、Token 策略、权限模型、Store 同步） | ✅ |
| [RABBITMQ.md](tech-design/RABBITMQ.md) | 消息队列拓扑、Exchange/Queue 设计、消息格式、死信处理 | ✅ |
| [DEPLOYMENT.md](tech-design/DEPLOYMENT.md) | 本地开发环境、生产部署、Nginx 配置、数据库迁移 | ✅ |
| [SANDBOX-RESEARCH.md](tech-design/SANDBOX-RESEARCH.md) | 沙箱机制调研报告（Docker vs CubeSandbox 对比） | ✅ |
| [INTEGRATION-CUBESANDBOX.md](tech-design/INTEGRATION-CUBESANDBOX.md) | CubeSandbox 集成设计（E2B SDK / REST API、API 设计、分级策略；runtime mock 已移除，测试 fake 独立在 `tests/sandbox/fakes.py`） | ✅ |
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
| [CHECKLIST.md](tasks/CHECKLIST.md) | 实现任务清单、核心开发闭环覆盖矩阵、TASK-012～TASK-026 路线图 | ✅ |

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
| TASK-009 | 2026-07-07 | SSE 执行过程可视化联调验证 | ✅ 已完成 |
| TASK-011 | 2026-07-07 | 高级设置面板真实透传 + 技术风险修正 | ✅ 已实现，验证中 |
| TASK-012 | 2026-07-08 | 核心开发闭环路线图与任务重排 | ✅ 已完成 |
| TASK-013 | 2026-07-08 | Project / Mount / Artifact 数据底座 | ✅ 已完成 |
| TASK-014 | 2026-07-08 | 项目管理页接真实数据 | ✅ 已完成 |
| TASK-015 | 2026-07-08 | PipelineRun / StageState 阶段状态机 | ✅ 已完成 |
| TASK-016 | 2026-07-08 | Artifact 产物归档与查看 | ✅ 已完成 |
| TASK-017 | 2026-07-08 | 人工确认与阶段继续机制 | ✅ 已完成 |
| TASK-018 | 2026-07-08 | Agent Bridge / 真实代码库读取 | ✅ 已完成 |
| TASK-019 | 2026-07-08 | 写回与交付闭环 | ✅ 已完成 |
| TASK-020 | 2026-07-08 | 服务端可信交付巩固 | ✅ 已完成 |
| TASK-021 | 2026-07-08 | 核心交互设计复盘与关键入口优化 | ✅ 已完成 |
| TASK-022 | 2026-07-08 | 交付能力扩展设计与实现 | ✅ 已完成 |
| TASK-023 | 2026-07-08 | GitHub OAuth Mount 授权底座 | ✅ 已完成 |
| TASK-024 | 2026-07-08 | GitHub PR Delivery | ✅ 已完成 |
| TASK-025 | 2026-07-08 | zip Delivery Package | ✅ 已完成 |
| TASK-026 | 2026-07-08 | Upload Mount 上下文兜底 | ✅ 已完成 |
| TASK-027～TASK-034 | 2026-07-09 | AI 架构收敛计划 | ✅ 已完成 |
| TASK-035 | 2026-07-10 | Stage 级 SkillPolicy 编排 | ✅ 已完成 |
| TASK-036 | 2026-07-10 | MCP RuntimeSpec 权限归一 | ✅ 已完成 |
| TASK-037 | 2026-07-10 | 内置 Skill RuntimeSpec 补齐 | ✅ 已完成 |
| TASK-038 | 2026-07-10 | 高风险 Skill 临时授权 | ✅ 已完成 |
| TASK-039 | 2026-07-10 | 高风险 Skill 授权确认入口 | ✅ 已完成 |

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

### TASK-009 详细信息
- **目录**：`docs/iterations/2026-07-07-task-009-sse-validation/`
- **产物**：
  - [TECHNICAL-DESIGN.md](iterations/2026-07-07-task-009-sse-validation/TECHNICAL-DESIGN.md)
  - [TEST-PLAN.md](iterations/2026-07-07-task-009-sse-validation/TEST-PLAN.md)
  - [ITERATION-REVIEW.md](iterations/2026-07-07-task-009-sse-validation/ITERATION-REVIEW.md)
- **核心功能**：执行步骤收集器、code_executor 单卡展示、stdout/stderr 补全、工具失败/超时状态自动化回归、浏览器 E2E 视觉验收

### TASK-011 详细信息
- **目录**：`docs/iterations/2026-07-07-task-011-risk-fixes/`
- **产物**：
  - [TECHNICAL-DESIGN.md](iterations/2026-07-07-task-011-risk-fixes/TECHNICAL-DESIGN.md)
- **核心功能**：高级设置状态持久化、上下文/阶段配置请求透传、system prompt 注入、沙箱配置和 API 路由前缀风险修正

### TASK-012 详细信息
- **目录**：`docs/iterations/2026-07-08-core-dev-workflow/`
- **产物**：
  - [PRODUCT-REQUIREMENTS.md](iterations/2026-07-08-core-dev-workflow/PRODUCT-REQUIREMENTS.md)
  - [TASK-CHECKLIST.md](iterations/2026-07-08-core-dev-workflow/TASK-CHECKLIST.md)
  - [TECHNICAL-DESIGN.md](iterations/2026-07-08-core-dev-workflow/TECHNICAL-DESIGN.md)
  - [TEST-PLAN.md](iterations/2026-07-08-core-dev-workflow/TEST-PLAN.md)
  - [ITERATION-REVIEW.md](iterations/2026-07-08-core-dev-workflow/ITERATION-REVIEW.md)
- **核心功能**：定义 Project → Mount → Session → PipelineRun → StageState → Artifact → Delivery 闭环，并拆出 TASK-013～TASK-019，避免 Project、Pipeline、Artifact、Bridge 和 Delivery 分散推进

### TASK-013 详细信息
- **核心功能**：Project、ProjectMount、Artifact SQLAlchemy 模型与 Alembic 迁移；Project/Mount/Artifact CRUD API；项目维度 Session API；旧 `/sessions` 默认项目兼容
- **验证**：`uv run --extra dev pytest` 通过；FastAPI uvicorn 启动到 `AgentForge startup complete ✓`

### TASK-014 详细信息
- **核心功能**：`projectsApi` 与 `useProjectStore`；Projects 页读取真实项目和主 Mount；创建向导创建 Project + primary Mount；ProjectBar 真实切换当前项目；Chat 会话按当前项目读取和新建
- **验证**：`npm run test:e2e -- projects.spec.ts` 通过；`npm run build` 通过

### TASK-015 详细信息
- **核心功能**：`PipelineRun` / `PipelineStageState` 模型与迁移；intent 到阶段配置；会话首次 chat 自动创建 PipelineRun；阶段 skip/restore/start/complete/fail API；StageRuntime 调用 SkillExecutionEngine 前后推进阶段；StagePreview 从后端 StageState 渲染
- **验证**：`uv run --extra dev pytest tests/api/test_pipeline_runs.py tests/pipeline/test_runtime.py` 通过；`npm run test:e2e -- pipeline-stage-state.spec.ts` 通过；`npm run build` 通过

### TASK-016 详细信息
- **核心功能**：StageRuntime 阶段完成后创建 Artifact；`artifact_created` SSE；会话消息回带关联 Artifact；Artifact Viewer；Chat ArtifactCard；Project 最近产物列表；Artifact 可加入下一轮上下文
- **验证**：`uv run --extra dev pytest tests/api/test_projects.py tests/api/test_pipeline_runs.py tests/pipeline/test_runtime.py` 通过；`npm run test:e2e -- artifact-viewer.spec.ts` 通过；`npm run build` 通过

### TASK-017 详细信息
- **核心功能**：`PipelineStageState` 确认字段与迁移；`waiting_confirmation` 状态；`confirm_required` / `confirm_resolved` SSE；确认 API 支持 approve/revise/cancel；StageRuntime 等待确认时停止推进；Chat ConfirmCard 可确认继续、提交修改意见或终止需求；确认操作写入审计日志
- **验证**：`uv run --extra dev pytest tests/api/test_pipeline_runs.py::test_confirmation_api_approves_or_revises_waiting_stage` 通过；`uv run --extra dev pytest tests/pipeline/test_runtime.py::test_stage_runtime_blocks_waiting_confirmation_stage` 通过；`npm run test:e2e -- human-confirmation.spec.ts` 通过；`npm run build` 通过

### TASK-018 详细信息
- **核心功能**：`agentforge mount <path>` CLI；Bridge 状态 API；授权 root 内目录列表与 UTF-8 文本读取；路径穿越和敏感文件拒绝；ContextPicker 浏览 connected local Mount 文件；Chat 请求携带 `mount_id` 后读取真实文件内容并注入 SkillExecutionEngine
- **验证**：`uv run --extra dev pytest tests/api/test_projects.py tests/api/test_bridge_cli.py tests/skills/test_engine_context.py` 通过；`npm run test:e2e -- bridge-context.spec.ts` 通过；`npm run build` 通过

### TASK-019 详细信息
- **核心功能**：`DeliveryService`；Artifact delivery 状态字段；Artifact Viewer 交付面板；unified diff 预览；`confirm_write` 后写回 connected local Mount；写前 `.agentforge.bak` 备份；Delivery report 保存和 Markdown 导出
- **验证**：`uv run --extra dev pytest tests/api/test_delivery.py` 通过；`npm run test:e2e -- artifact-viewer.spec.ts` 通过

### TASK-020～TASK-026 详细信息
- **目录**：`docs/iterations/2026-07-08-core-strengthening/`
- **产物**：
  - [PRODUCT-REQUIREMENTS.md](iterations/2026-07-08-core-strengthening/PRODUCT-REQUIREMENTS.md)
  - [TASK-CHECKLIST.md](iterations/2026-07-08-core-strengthening/TASK-CHECKLIST.md)
  - [TECHNICAL-DESIGN.md](iterations/2026-07-08-core-strengthening/TECHNICAL-DESIGN.md)
  - [UI-REVIEW.md](iterations/2026-07-08-core-strengthening/UI-REVIEW.md)
  - [TEST-PLAN.md](iterations/2026-07-08-core-strengthening/TEST-PLAN.md)
  - [ITERATION-REVIEW.md](iterations/2026-07-08-core-strengthening/ITERATION-REVIEW.md)
- **核心功能**：先加固 Delivery preview/apply 一致性、失败落库和审计日志；再让 Project、Chat、Stage、Artifact 的下一步动作可见；然后设计并落地 GitHub OAuth Mount、GitHub PR Delivery、zip Delivery Package 和 Upload Mount 上下文兜底。

### TASK-027～TASK-034 详细信息
- **目录**：`docs/iterations/2026-07-09-ai-architecture-convergence/`
- **产物**：
  - [PRODUCT-REQUIREMENTS.md](iterations/2026-07-09-ai-architecture-convergence/PRODUCT-REQUIREMENTS.md)
  - [TASK-CHECKLIST.md](iterations/2026-07-09-ai-architecture-convergence/TASK-CHECKLIST.md)
  - [TECHNICAL-DESIGN.md](iterations/2026-07-09-ai-architecture-convergence/TECHNICAL-DESIGN.md)
  - [TEST-PLAN.md](iterations/2026-07-09-ai-architecture-convergence/TEST-PLAN.md)
  - [ITERATION-REVIEW.md](iterations/2026-07-09-ai-architecture-convergence/ITERATION-REVIEW.md)
  - [TASK-027.md](iterations/2026-07-09-ai-architecture-convergence/TASK-027.md)
  - [TASK-028.md](iterations/2026-07-09-ai-architecture-convergence/TASK-028.md)
  - [TASK-029.md](iterations/2026-07-09-ai-architecture-convergence/TASK-029.md)
  - [TASK-030.md](iterations/2026-07-09-ai-architecture-convergence/TASK-030.md)
  - [TASK-031.md](iterations/2026-07-09-ai-architecture-convergence/TASK-031.md)
  - [TASK-032.md](iterations/2026-07-09-ai-architecture-convergence/TASK-032.md)
  - [TASK-033.md](iterations/2026-07-09-ai-architecture-convergence/TASK-033.md)
  - [TASK-034.md](iterations/2026-07-09-ai-architecture-convergence/TASK-034.md)
- **核心功能**：把 AgentForge 的长期 AI 架构收敛为 Project → Intent → Pipeline → Stage → Agent/Profile → Skill Runtime → Artifact → Delivery → Eval Feedback 主链路。TASK-027～TASK-034 已完成运行时契约、Pipeline Catalog、Agent 绑定、模型路由、第三方 Skill 导入闭环、Governance 人工确认策略、Eval Feedback 结构化反馈闭环和架构文档收敛。

### TASK-035 详细信息
- **目录**：`docs/iterations/2026-07-10-stage-skill-policy/`
- **产物**：
  - [PRODUCT-REQUIREMENTS.md](iterations/2026-07-10-stage-skill-policy/PRODUCT-REQUIREMENTS.md)
  - [TASK-CHECKLIST.md](iterations/2026-07-10-stage-skill-policy/TASK-CHECKLIST.md)
  - [TECHNICAL-DESIGN.md](iterations/2026-07-10-stage-skill-policy/TECHNICAL-DESIGN.md)
  - [TEST-PLAN.md](iterations/2026-07-10-stage-skill-policy/TEST-PLAN.md)
  - [ITERATION-REVIEW.md](iterations/2026-07-10-stage-skill-policy/ITERATION-REVIEW.md)
- **核心功能**：StageRuntime 在调用 SkillExecutionEngine 前按 `StageDefinition.skill_policy_key`、`AgentProfile.allowed_skill_names` 和 `SkillRuntimeSpec.permissions` 过滤 LLM 可见工具；SkillDispatcher 继续保留调用前权限校验。

### TASK-036 详细信息
- **目录**：`docs/iterations/2026-07-10-mcp-runtime-spec/`
- **产物**：
  - [PRODUCT-REQUIREMENTS.md](iterations/2026-07-10-mcp-runtime-spec/PRODUCT-REQUIREMENTS.md)
  - [TASK-CHECKLIST.md](iterations/2026-07-10-mcp-runtime-spec/TASK-CHECKLIST.md)
  - [TECHNICAL-DESIGN.md](iterations/2026-07-10-mcp-runtime-spec/TECHNICAL-DESIGN.md)
  - [TEST-PLAN.md](iterations/2026-07-10-mcp-runtime-spec/TEST-PLAN.md)
  - [ITERATION-REVIEW.md](iterations/2026-07-10-mcp-runtime-spec/ITERATION-REVIEW.md)
- **核心功能**：MCP Server 配置支持 permissions 声明；未声明 permissions 的 MCP 默认按 `credential` 高风险处理；MCP 注册到 SkillRegistry 时写入 `source_type=mcp` 的 RuntimeSpec，并复用 StageSkillPolicy 过滤。

### TASK-037 详细信息
- **目录**：`docs/iterations/2026-07-10-builtin-runtime-spec/`
- **产物**：
  - [PRODUCT-REQUIREMENTS.md](iterations/2026-07-10-builtin-runtime-spec/PRODUCT-REQUIREMENTS.md)
  - [TASK-CHECKLIST.md](iterations/2026-07-10-builtin-runtime-spec/TASK-CHECKLIST.md)
  - [TECHNICAL-DESIGN.md](iterations/2026-07-10-builtin-runtime-spec/TECHNICAL-DESIGN.md)
  - [TEST-PLAN.md](iterations/2026-07-10-builtin-runtime-spec/TEST-PLAN.md)
  - [ITERATION-REVIEW.md](iterations/2026-07-10-builtin-runtime-spec/ITERATION-REVIEW.md)
- **核心功能**：新增 `external_side_effect` 高风险权限；五个内置 Skill 注册时写入 `source_type=builtin` 的 RuntimeSpec；默认 StageSkillPolicy 只暴露 `web_search` 和 `get_weather`。

### TASK-038 详细信息
- **目录**：`docs/iterations/2026-07-10-high-risk-skill-authorization/`
- **产物**：
  - [PRODUCT-REQUIREMENTS.md](iterations/2026-07-10-high-risk-skill-authorization/PRODUCT-REQUIREMENTS.md)
  - [TASK-CHECKLIST.md](iterations/2026-07-10-high-risk-skill-authorization/TASK-CHECKLIST.md)
  - [TECHNICAL-DESIGN.md](iterations/2026-07-10-high-risk-skill-authorization/TECHNICAL-DESIGN.md)
  - [TEST-PLAN.md](iterations/2026-07-10-high-risk-skill-authorization/TEST-PLAN.md)
  - [ITERATION-REVIEW.md](iterations/2026-07-10-high-risk-skill-authorization/ITERATION-REVIEW.md)
- **核心功能**：StageRuntime 支持 `advanced_context.skill_authorization` 阶段级临时授权；`SkillPolicy` 可按 `authorized_skill_names` / `authorized_permissions` 放行当前阶段高风险 Skill，同时保持 AgentSkill allowlist 不可绕过。

### TASK-039 详细信息
- **目录**：`docs/iterations/2026-07-10-high-risk-skill-confirmation/`
- **产物**：
  - [PRODUCT-REQUIREMENTS.md](iterations/2026-07-10-high-risk-skill-confirmation/PRODUCT-REQUIREMENTS.md)
  - [TASK-CHECKLIST.md](iterations/2026-07-10-high-risk-skill-confirmation/TASK-CHECKLIST.md)
  - [TECHNICAL-DESIGN.md](iterations/2026-07-10-high-risk-skill-confirmation/TECHNICAL-DESIGN.md)
  - [TEST-PLAN.md](iterations/2026-07-10-high-risk-skill-confirmation/TEST-PLAN.md)
  - [ITERATION-REVIEW.md](iterations/2026-07-10-high-risk-skill-confirmation/ITERATION-REVIEW.md)
- **核心功能**：StageRuntime 对被默认策略过滤的已绑定高风险 Skill 发出 `skill_authorization_required` SSE；Chat 前端展示授权卡片，用户确认后以一次性 `skill_authorization` payload 重试当前消息。

## 版本号规范

- 新迭代目录：`docs/iterations/YYYY-MM-DD-topic/`
- 标准产物：`PRODUCT-REQUIREMENTS.md`、`TASK-CHECKLIST.md`、`TECHNICAL-DESIGN.md`、`TEST-PLAN.md`、`ITERATION-REVIEW.md`
- UI 相关迭代增加：`UI-DESIGN.md`
- 历史 `PRD-*`、`TASK-*`、`TEST-*`、`ITER-*` 文件保留可追溯，后续新迭代使用新命名规范
