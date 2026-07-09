# AI 架构收敛计划产品需求

## 1. 背景

AgentForge 已经具备 Project / Mount / Session / PipelineRun / StageState / Artifact / Delivery 的核心开发闭环，也有 Agent 管理、Skill 管理、LLM 设置、交付与导出等基础能力。

当前问题不是“项目不可用”，而是能力已经铺开后，需要把 AI 运行时收敛成更稳定的长期架构。否则后续继续增加 Agent、Skill、模型、阶段和交付方式时，容易出现以下问题：

- 前端和后端各自维护阶段语义，需求类型和流水线容易漂移。
- Agent 页面能创建配置，但运行时选择链路不够明确。
- Skill 可以安装和展示，但第三方导入、权限、运行时注册、审计尚未完全闭环。
- LLM 配置偏全局，缺少 Provider / Model / Credential / Route 的可治理结构。
- 阶段执行结果有产物和交付，但缺少系统化评估反馈，难以长期变快、变稳。

本次迭代的目标是把 AgentForge 从“多 Agent 能力集合”推进到“以项目为中心的 AI 开发操作系统”。

## 2. 产品定位

长期定位：

```text
AgentForge = Project-centered AI Development OS
```

核心链路：

```text
Project
  -> Intent
  -> Pipeline
  -> Stage
  -> Agent/Profile
  -> Skill Runtime
  -> Artifact
  -> Delivery
  -> Eval Feedback
```

这条链路的核心价值是：用稳定的软件工程对象包住不稳定的 AI 行为，让平台可以更快迭代、更稳交付、更容易排查问题。

## 3. 目标

### G1. 让 AI 执行链路有统一运行时契约

所有 AI 执行都必须能回答：

- 属于哪个 Project。
- 来源于哪类 Intent。
- 当前处于哪个 Pipeline Stage。
- 使用哪个 Agent Profile。
- 使用哪个 Model Route。
- 可调用哪些 Skill。
- 生成了哪些 Artifact。
- 是否需要人工确认。
- 交付结果和评估结果是什么。

### G2. 让 Pipeline 成为后端唯一事实源

需求类型、阶段定义、阶段依赖、人工确认点、阶段输出物和可用动作由后端统一定义，前端只负责展示和交互，不再重复维护业务语义。

### G3. 让 Agent 从配置页走入运行时

Agent 创建后必须能明确作用于运行时：

- 按需求类型或阶段选择默认 Agent。
- Agent 控制模型路由、能力、Skill 白名单和系统提示策略。
- 执行记录能追溯到具体 Agent Profile。

### G4. 让模型配置可治理

模型不再只是一个全局字段，而是由 Provider、Model、Credential、Route 和 Policy 组成：

- Provider 定义供应商。
- Model 定义模型能力和价格元数据。
- Credential 安全保存密钥。
- Route 决定不同阶段用哪个模型和兜底模型。
- Policy 控制预算、超时、重试和禁用范围。

### G5. 让 Skill 市场具备可扩展闭环

第三方 Skill 不只是展示入口，而要有完整生命周期：

- Manifest 校验。
- 安装预览。
- 权限声明。
- 运行时注册。
- 调用审计。
- 禁用和卸载。

### G6. 让人工确认和风险治理成为平台能力

人工介入点不能散落在具体页面和单个阶段里，需要统一策略：

- PRD / 需求 Diff 确认。
- 技术选型确认。
- 影响范围确认。
- 写回和交付确认。
- 高风险 Skill 调用确认。

### G7. 建立评估反馈闭环

平台需要沉淀每次 AI 执行的质量数据：

- 阶段通过率。
- 人工修改率。
- 产物采纳率。
- Skill 成功率。
- 模型成本和延迟。
- 失败原因分类。

这些数据用于后续优化 Agent Profile、Prompt、阶段编排、模型路由和 Skill 策略。

## 4. 用户故事

| ID | 用户故事 | 价值 |
|----|----------|------|
| US-1 | 作为全栈开发工程师，我希望每个项目的 AI 执行都有清晰阶段和产物，而不是一段不可复盘的聊天记录。 | 方便追踪、复用和交付 |
| US-2 | 作为独立开发者，我希望不同任务自动选择合适的 Agent、模型和 Skill，而不用每次手动配置。 | 降低操作成本 |
| US-3 | 作为团队成员，我希望高风险修改前能看到影响范围并确认，避免 AI 直接改坏代码。 | 提升安全性 |
| US-4 | 作为维护多个项目的人，我希望 Skill、模型密钥和 Agent 策略可管理、可审计、可禁用。 | 支撑长期使用 |
| US-5 | 作为平台维护者，我希望每次 AI 执行都能被评估，知道哪里慢、哪里贵、哪里容易失败。 | 支撑持续优化 |

## 5. 功能范围

### R-001. AI Runtime Contract

定义统一运行时上下文对象，贯穿 Pipeline、StageRuntime、SkillExecutionEngine、Artifact 和 Delivery。

### R-002. Pipeline Stage Catalog

建立后端阶段目录，支持按 intent type 返回阶段配置、确认策略、输出物和可用动作。

### R-003. Agent Runtime Binding

让 Agent Profile 参与阶段执行选择，支持阶段默认 Agent、项目默认 Agent 和用户手动覆盖。

### R-004. Model Provider / Credential / Route

拆分模型供应商、模型、密钥和路由策略，支持阶段级模型选择和兜底。

### R-005. Skill Import Lifecycle

完善第三方 Skill 导入、安装、权限、注册、审计、禁用、卸载链路。

### R-006. Governance Policy

将人工确认、影响范围和高风险动作统一为可配置策略。

### R-007. Eval Feedback

记录执行指标和质量反馈，为后续优化提供数据基础。

### R-008. Architecture Convergence Docs

同步更新架构文档、API 说明和迭代索引，避免蓝图和真实代码继续分叉。

## 6. 非目标

本次计划不直接承诺以下事项：

- 不做完全无人值守的自动上线。
- 不默认允许任意第三方 Skill 执行本地命令。
- 不在 Web 端强行实现浏览器受限的本地目录任意选择能力；Web 端只能通过 Bridge / CLI / Desktop / File System Access API 等授权边界实现。
- 不一次性重写现有 Harness、Pipeline、SkillEngine，而是按任务逐步收敛。
- 不把 UI 视觉重设计作为本次主目标；涉及 UI 的任务只服务于运行时可见性和配置闭环。

## 7. 成功指标

| 指标 | 目标 |
|------|------|
| 阶段定义漂移 | 前端不再硬编码核心阶段语义 |
| Agent 运行时可追溯 | 每次执行能记录 agent_profile_id 或默认策略来源 |
| 模型配置可治理 | 密钥、模型、路由、兜底策略可被后台管理 |
| Skill 调用可审计 | 第三方 Skill 调用有权限声明和审计记录 |
| 高风险动作可控 | 影响范围、技术选型、写回交付有统一确认策略 |
| 执行质量可评估 | PipelineRun / Stage / Skill / Model 维度有基础指标 |
| 回归稳定性 | 后端 pytest、前端 build、FastAPI 启动验证保持通过 |

## 8. 风险与约束

| 风险 | 影响 | 缓解策略 |
|------|------|----------|
| 抽象过重 | 迭代速度变慢 | 每个任务必须落到当前模块和可验收代码，不做空泛平台化 |
| 迁移破坏旧流程 | 用户现有页面不可用 | 保持 API 兼容，先新增后切换 |
| 密钥管理不当 | 安全风险 | Credential 只返回 masked 信息，严禁日志输出明文 |
| Skill 扩展失控 | 本地环境风险 | Manifest 权限白名单、禁用默认本地命令执行 |
| Eval 数据噪声大 | 指标误导 | 先收集结构化事件，再逐步建立评分 |

## 9. 任务拆分

本计划拆为 `TASK-027` 到 `TASK-034`：

| 任务 | 主题 | 优先级 |
|------|------|--------|
| TASK-027 | AI Runtime Baseline 与契约文档 | P0 |
| TASK-028 | Pipeline Stage Catalog 后端唯一事实源 | P0 |
| TASK-029 | Agent Profile 运行时绑定 | P0 |
| TASK-030 | LLM Provider / Model / Credential / Route | P0 |
| TASK-031 | 第三方 Skill 导入与运行时闭环 | P1 |
| TASK-032 | Governance 与人工确认策略引擎 | P1 |
| TASK-033 | Eval Feedback 执行质量反馈闭环 | P1 |
| TASK-034 | 架构文档收敛与迁移清理 | P2 |
