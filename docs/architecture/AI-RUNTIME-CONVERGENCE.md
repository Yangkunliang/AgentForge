# AI Runtime 收敛架构

本文档定义 AgentForge 长期 AI 架构的主线、当前实现基线、目标运行时契约和迁移任务边界。它是 TASK-027 的产物，并在 TASK-034 后成为 AI Runtime 当前推荐阅读入口；TASK-035 后，Stage 级 SkillPolicy 已进入运行时工具过滤链路。

## 1. 定位

AgentForge 的长期形态不是“多 Agent 聊天页”，而是面向全栈开发工程师的项目级 AI 开发操作系统：

```text
Project -> Intent -> Pipeline -> Stage -> Agent/Profile -> Skill Runtime -> Artifact -> Delivery -> Eval Feedback
```

这条链路的核心价值是：用稳定的软件工程对象包住不稳定的 AI 行为，让每次执行都能被规划、观察、确认、交付和复盘。

## 2. 当前真实链路

截至 TASK-035，代码里的主链路已经具备 Project-first 基础，并已把 Pipeline 阶段定义、AgentProfile、ModelRoute、第三方 Skill Runtime、StageSkillPolicy、GovernanceDecision 和 EvalFeedback 接入统一 AI Runtime Contract。

### 2.1 请求到执行

```text
src/api/routes/sessions.py
  -> _run_task_with_skills()
  -> LLMConfig(settings.default_model, temperature, max_tokens)
  -> SkillRegistry.get_all_tool_defs()
  -> StageRuntime.run_current_stage()
```

现状：

- Chat 入口会创建 Task、Message，并在后台任务中执行。
- 用户自定义助手名来自 `UserAgentSettings.agent_name`，传给 SkillExecutionEngine 的 system prompt。
- 模型选择来自全局 settings 的 `default_model`。
- 工具列表来自全局 SkillRegistry，但 StageRuntime 会在调用 SkillExecutionEngine 前按 StageSkillPolicy 和 AgentProfile allowlist 过滤。

缺口：

- Agent 管理页创建的 active `Agent` 已可通过 AgentResolver 进入 StageRuntime 选择链路。

### 2.2 Pipeline 状态机

```text
src/agent_forge/pipeline/catalog.py
  -> PIPELINE_CATALOG
src/agent_forge/pipeline/service.py
  -> create_pipeline_run_for_session()
  -> PipelineRun + PipelineStageState
src/agent_forge/pipeline/runtime.py
  -> start_stage()
  -> SkillExecutionEngine.run()
  -> complete_stage()
```

现状：

- `PIPELINE_CATALOG` 是 intent -> StageDefinition 的后端唯一事实源。
- `PipelineRun` 记录 intent、状态、current_stage_id。
- `PipelineStageState` 记录阶段状态、是否 required、是否 confirmation_required，以及确认类型、原因、影响范围和审计 payload。
- `StageRuntime` 从 Catalog 读取 StageDefinition，负责 stage started / completed / failed 与 SSE。
- confirmation_required 阶段完成后进入 `waiting_confirmation`。
- 前端通过 `/api/v1/pipeline/catalog` 读取阶段定义、默认动作和 placeholder。

缺口：

- StageDefinition 已包含输出物类型、默认 Agent selector、模型路由 key 和 Skill policy key；`default_agent_selector` 已绑定 AgentResolver，`model_route_key` 已绑定 ModelRouter，`skill_policy_key` 已绑定 Stage 级工具过滤，确认策略已绑定 GovernancePolicy，SkillDispatcher 仍保留 Skill 调用前权限校验。
- ConfirmCard 已渲染 GovernancePolicy 生成的确认原因和影响范围。
- 前端仍保留 intent 展示 label/icon，但阶段业务语义已以后端 Catalog 为准。

### 2.3 Skill Runtime

```text
src/agent_forge/skills/registry.py
  -> SkillRegistry.register()
  -> get_all_tool_defs()
src/agent_forge/skills/engine.py
  -> llm.tool_use_complete(messages, tools, config)
  -> SkillDispatcher.invoke()
src/agent_forge/skills/dispatcher.py
  -> registry.get_executor(tool_name)
```

现状：

- 内置 Skill 和 MCP tool 可以注册到 SkillRegistry。
- SkillExecutionEngine 实现 ReAct tool_use 循环。
- SkillDispatcher 支持超时、SSE 事件、tracing、权限校验、审计和 `skill_eval` 事件。
- `SkillInstaller` 支持外部 Skill import preview/install，安装前展示来源、工具、权限、风险和确认要求。
- `SkillManifest` 支持 `agentforge-skill.yaml` 优先、`skill.md` 兼容，统一生成 `SkillRuntimeSpec`。
- `SkillRegistry` 保存 runtime spec 和 tool -> skill 映射，安装后可刷新第三方 Skill executor。

缺口：

- `filter_tool_defs_for_runtime()` 会按 `StageDefinition.skill_policy_key`、`AgentProfile.allowed_skill_names` 和 `SkillRuntimeSpec.permissions` 过滤 LLM 可见工具。
- GovernancePolicy 已兜底高风险 Skill 权限确认；默认 StageSkillPolicy 不主动暴露 `shell`、`filesystem`、`credential` 高风险权限工具。
- MCP Tool 尚未全部归一化成带权限声明的 SkillRuntimeSpec。

### 2.4 LLM Provider

```text
src/agent_forge/llm/provider.py
src/agent_forge/llm/router.py
  -> LLMConfig(model, temperature, max_tokens, timeout, api_key, api_base)
  -> LiteLLMProvider
  -> FallbackLLMProvider
```

现状：

- LLMProvider 支持 complete、chat_complete、stream_complete、tool_use_complete。
- stream_complete 支持 thinking 事件拆分。
- LiteLLMProvider 可使用 ModelRouter 解析出的 model、api_key、api_base，也保留 settings legacy fallback。
- FallbackLLMProvider 能在 litellm 不可用时降级。
- `ModelRouter` 会按 requested route 解析 Provider / Model / Credential / Route，不可用时尝试 fallback_route_keys，最后退回 legacy settings。
- LLM Credential 服务端加密存储，API 和运行时 prompt 只使用 masked 或非敏感引用。

缺口：

- 预算和重试策略字段已预留，尚未纳入统一 Governance / Eval 统计。
- Artifact 尚未记录生成它的 ModelRoute 引用。

### 2.5 Artifact 和 Delivery

```text
StageRuntime._complete_stage()
  -> create_stage_artifact()
  -> emit_artifact_created()
Artifact Viewer
  -> DeliveryService preview/apply
```

现状：

- 阶段输出会归档为 Artifact。
- Artifact 可被 Chat、Project、Viewer 使用。
- Delivery 已支持本地写回、GitHub PR、zip 包。
- Delivery preview/apply 有一致性校验和失败报告。

缺口：

- Artifact 自身尚未持久化生成它的 AgentProfile、ModelRoute、SkillRuntime 引用；这些运行事实已进入 EvalEvent。
- Delivery 结果已进入统一 Eval Feedback。

## 3. 目标运行时契约

AI Runtime Contract 是跨 Pipeline、Agent、LLM、Skill、Artifact、Delivery 和 Eval 的稳定上下文。后续任务应优先复用这些对象名，避免每个模块再发明一套概念。

### 3.1 ProjectRuntimeContext

作用：描述一次执行所属的项目、会话、授权代码库和安全边界。

字段方向：

```text
project_id
session_id
pipeline_run_id
user_id
mounts
active_mount_id
workspace_policy
delivery_policy
audit_context
```

当前映射：

- `Project`、`ProjectMount`、`Session` 已存在。
- Bridge 和 Delivery 已受 Mount 边界约束。
- audit_context 分散在 AuditLog 调用中。

后续收敛：

- 后续 StageRuntime 应显式接收或构建 ProjectRuntimeContext，避免 Project / Mount / Delivery / Audit 边界继续分散。
- Delivery 和 SkillPolicy 复用同一授权边界。

### 3.2 IntentDecision

作用：表示用户需求分类结果，并决定 Pipeline。

字段方向：

```text
intent_type
confidence
reason
risk_level
required_capabilities
pipeline_key
```

当前映射：

- `Session.intent_type` 和 `PipelineRun.intent_type` 已存在。
- `normalize_intent()` 当前把未知类型回退为 `iteration`。

后续收敛：

- Pipeline Catalog 已把 intent 到阶段的映射服务化；后续可把 confidence、reason 和 risk_level 写入 PipelineRun metadata 或独立 IntentDecision 表。
- 未来可把 confidence、reason 和 risk_level 写入 PipelineRun metadata 或独立 IntentDecision 表。

### 3.3 StageDefinition

作用：定义阶段业务语义、运行策略和前端渲染事实源。

字段方向：

```text
key
name
description
order
required
required_inputs
output_artifact_types
confirmation_policy
default_agent_selector
model_route_key
skill_policy_key
can_skip
can_restore
```

当前映射：

- `StageDefinition(stage_id, stage_name, description, required, confirmation_required, output_artifact_types, default_agent_selector, model_route_key, skill_policy_key)` 已存在。
- `PipelineStageState` 保存阶段运行状态。
- `Pipeline Catalog API` 已向前端提供 intent 对应阶段、确认策略和默认快捷动作。

后续收敛：

- `default_agent_selector` 已绑定到真实 AgentProfile。
- `model_route_key` 已绑定到真实 ModelRoute。
- `skill_policy_key` 已接入 Stage 级可用 Skill 过滤。

### 3.4 AgentProfile

作用：把后台 Agent 配置接入运行时选择。

字段方向：

```text
id
name
capabilities
default_model_route_key
allowed_skill_names
system_policy_key
stage_preferences
enabled
```

当前映射：

- `Agent` 模型已有 name、capabilities、model、status、avatar_url。
- `AgentResolver` 已把 active Agent 解析成运行时 AgentProfile。
- `PipelineStageState` 已记录 agent_profile_id、agent_profile_name、agent_profile_source。
- `UserAgentSettings` 当前只影响 assistant 名称和头像。
- StageRuntime 接收 fallback `agent_name`，但会优先使用 AgentResolver 返回的 AgentProfile name 和上下文。

后续收敛：

- AgentProfile 的 model_name / default_model_route_key 已交给 ModelRouter 做 fallback。
- AgentProfile 的 allowed_skill_names 来自启用的 `AgentSkill` 绑定，并参与 SkillPolicy 工具过滤。
- `UserAgentSettings` 继续负责个人助手展示名，不等同于 AgentProfile。

### 3.5 ModelRoute

作用：按阶段、Agent 和策略解析模型供应商、密钥、超时、重试和兜底。

字段方向：

```text
route_key
provider_key
model_key
credential_ref
fallback_route_keys
budget_policy
timeout_seconds
retry_policy
enabled
```

当前映射：

- `LLMConfig` 保存单次调用的 model、temperature、max_tokens、timeout、api_key、api_base、provider_key。
- `LLMProviderSetting`、`LLMModelSetting`、`LLMCredential`、`LLMRoute` 已保存 Provider / Model / Credential / Route。
- `LLMCredential.encrypted_secret` 服务端加密，API 只返回 `masked_secret`。
- `StageRuntime` 会解析当前阶段的 ModelRoute，写入 `PipelineStageState.model_route_key/name/source` 和 `model_name`。

后续收敛：

- 旧全局配置作为 legacy fallback 保留，后续可提供一键迁移成 default route。
- `budget_policy` 和 `retry_policy` 字段已预留，后续接入 Governance / Eval。

### 3.6 SkillRuntimeSpec

作用：统一描述内置 Skill、外部 Skill 和 MCP Tool 的运行时能力。

字段方向：

```text
name
version
source_type
manifest_hash
tool_defs
permissions
executor_kind
enabled
audit_level
```

当前映射：

- `Skill` DB 模型记录管理态 Skill。
- `Skill` DB 模型记录 manifest_hash、permissions、runtime_spec 和 audit_level。
- `SkillInstall` 记录安装预览、manifest_hash、permissions 和 risk_level。
- `SkillRegistry` 记录 tool_defs、executor、runtime_spec 和 tool -> skill 映射。
- `SkillInstaller` 支持本地、Git/GitHub、PyPI 源的安装前预览；本地安装会复制到 `skills/installed/` 并刷新 registry。
- `SkillDispatcher` 调用前检查权限，调用后写审计并发出 `skill_eval` 事件。

后续收敛：

- TASK-032 已将高风险权限确认接入 GovernancePolicy，并把拒绝审计写入 `governance_decision`；Stage 级可用 Skill 白名单仍可后续增强。
- `skill_eval` SSE 事件已沉淀为结构化 EvalEvent。

### 3.7 GovernanceDecision

作用：统一表达是否允许、拒绝或要求人工确认。

字段方向：

```text
decision
reason
risk_level
confirmation_type
impact_scope
audit_payload
```

当前映射：

- `src/agent_forge/governance/policy.py` 定义 `GovernanceDecision` 和 `GovernancePolicy`。
- `PipelineStageState.confirmation_required/type/reason/impact_scope/audit_payload` 支持阶段确认上下文。
- Delivery 本地写回、GitHub PR、zip 包在缺少确认时统一输出 `missing_confirmation` 决策。
- 高风险 Skill 权限调用前会经由 GovernancePolicy，并在 `skill.invoke.denied` 审计中记录确认类型、风险等级、权限和影响范围。

后续收敛：

- TASK-033 可复用 GovernanceDecision 的审计 payload 作为 EvalFeedback 的风险和用户确认事实。

### 3.8 EvalFeedback

作用：记录执行质量、成本、延迟、失败原因和用户采纳情况。

字段方向：

```text
pipeline_run_id
stage_key
agent_profile_id
model_route_key
skill_name
artifact_id
delivery_channel
status
latency_ms
cost_amount
user_action
failure_reason
score
```

当前映射：

- LLMResponse 有 tokens_used、cost_usd、latency_ms。
- SkillDispatcher span 记录 elapsed_ms、success、error。
- `EvalEvent` 记录 project、pipeline_run、stage、agent_profile、model_route、skill、artifact、delivery、latency、cost、failure_reason 和 metadata。
- `EvaluationService.safe_record_event()` 使用独立 session 写入，失败只记录日志，不阻断主链路。
- StageRuntime、SkillDispatcher、Pipeline 确认和 Delivery 成功/失败路径已写入 EvalEvent。
- Dashboard 和 `/api/v1/evaluation/summary` 已消费 EvalEvent 基础指标。
- ExportManager 支持 `eval_events` / `evaluation` JSONL 导出。

后续收敛：

- LLMProvider 级 token/cost 明细可继续接入 EvalEvent。
- 用户采纳评分和长期质量 score 可作为后续反馈模型加入。

## 4. 目标数据流

```mermaid
flowchart LR
  P["ProjectRuntimeContext"] --> I["IntentDecision"]
  I --> C["Pipeline Catalog"]
  C --> R["PipelineRun"]
  R --> S["StageRuntime"]
  S --> A["AgentResolver"]
  A --> M["ModelRouter"]
  A --> K["SkillPolicy"]
  M --> L["LLMProvider"]
  K --> G["SkillRuntimeSpec"]
  L --> E["SkillExecutionEngine"]
  G --> E
  E --> O["Artifact"]
  O --> D["Delivery"]
  D --> F["EvalFeedback"]
  F --> C
  F --> A
  F --> M
```

StageRuntime 是收敛点，不是所有逻辑都堆进 StageRuntime。它只负责组装上下文并协调以下组件：

| 组件 | 职责 |
|------|------|
| Pipeline Catalog | 根据 IntentDecision 返回 StageDefinition |
| AgentResolver | 根据 Project、Stage、用户覆盖选择 AgentProfile |
| ModelRouter | 根据 StageDefinition 和 AgentProfile 选择 ModelRoute |
| SkillPolicy | 根据 StageDefinition 和 AgentProfile 过滤 SkillRuntimeSpec |
| GovernancePolicy | 对阶段、Skill、Delivery 做 allow / require_confirmation / deny 决策 |
| SkillExecutionEngine | 执行 LLM ↔ Tool 的 ReAct 循环 |
| ArtifactService | 保存阶段产物 |
| DeliveryService | 预览和应用交付 |
| EvaluationService | 记录质量反馈事件 |

## 5. 模块映射

| 目标对象 | 当前代码 | 当前状态 | 下一任务 |
|----------|----------|----------|----------|
| ProjectRuntimeContext | `models/project.py`、`bridge/`、`delivery/`、`sessions.py` | Project/Mount/Session 已落地，context 未统一对象化 | 后续增强 |
| IntentDecision | `pipeline/catalog.py`、`sessions.py` | intent_type -> catalog 已落地，缺 confidence/reason/risk | 后续增强 |
| StageDefinition | `pipeline/catalog.py`、`PipelineStageState` | 后端 Catalog 已落地，前端从 API 读取核心阶段语义，并写入 Governance 确认上下文 | 后续增强 |
| AgentProfile | `models/agent.py`、`agents/resolver.py`、`PipelineStageState` | active Agent 已绑定 StageRuntime，可追溯 agent_profile_id/name/source | 后续增强 |
| ModelRoute | `llm/router.py`、`models/llm.py`、`PipelineStageState`、`api/routes/llm.py` | Provider/Model/Credential/Route 已落地，StageRuntime 可追溯 model route | 后续增强 |
| SkillRuntimeSpec | `skills/registry.py`、`skills/installer.py`、`skills/runtime_spec.py`、`skills/policy.py` | Manifest、权限、runtime spec、registry 刷新、Stage 级工具过滤、调用审计和高风险 Governance 决策已落地 | 后续增强 |
| GovernanceDecision | `governance/policy.py`、`pipeline/service.py`、`pipeline_runs.py`、`projects.py`、`skills/policy.py` | 阶段、交付和高风险 Skill 调用已走统一决策，并写入确认上下文、审计 payload 和 EvalEvent 确认事实 | 后续增强 |
| EvalFeedback | `evaluation/service.py`、`models/evaluation.py`、`api/routes/evaluation.py`、StageRuntime、SkillDispatcher、Delivery | EvalEvent、Evaluation summary、Dashboard 聚合和 JSONL 导出已落地 | 后续增强 |
| 架构文档 | `docs/architecture/`、`docs/tech-design/`、`docs/README.md`、`MEMORY.md`、`CLAUDE.md` | 已完成 AI Runtime 主线、核心闭环、Agent、LLM、Skill、安全、API、数据库和导出文档收敛 | 持续维护 |

## 6. 迁移原则

1. 不推倒重写。优先复用现有 Project / Pipeline / Skill / Delivery 基础。
2. 后端事实源优先。Pipeline、Agent、Model、Skill 和 Governance 的核心语义必须以后端为准。
3. 配置对象要进入运行时。后台页面不是孤岛，保存的 Agent、Skill、ModelRoute 必须影响 StageRuntime。
4. 人工确认是策略，不是页面按钮。所有高风险动作都应能被 GovernancePolicy 解释。
5. Eval 先记录事实，再做评分。第一版 EvaluationService 只要求结构化、可查询、低侵入。
6. 安全边界不可弱化。Mount 授权、Credential 脱敏、Skill 权限、Delivery 一致性校验必须持续保留。

## 7. TASK-028 到 TASK-034 边界

### TASK-028: Pipeline Stage Catalog

目标：把 `PIPELINE_CONFIGS` 升级为后端阶段目录，让前端和 StageRuntime 消费同一份 StageDefinition。

完成状态：已落地 `src/agent_forge/pipeline/catalog.py` 和 `/api/v1/pipeline/catalog`，StageRuntime、PipelineService 和前端 Pipeline Store 均消费后端 Catalog。

不做：

- 不引入复杂 AI intent 分类器。
- 不改变已存在 PipelineRun 状态机语义。

### TASK-029: Agent Profile 运行时绑定

目标：让 `Agent` 管理态配置进入 StageRuntime，形成可追溯 AgentProfile。

完成状态：已落地 AgentResolver、StageRuntime agent_profile 追踪、运行时 Agent 候选 API、SkillExecutionEngine agent_profile 上下文和前端当前阶段 Agent 展示。

不做：

- 不把 `UserAgentSettings.agent_name` 误当成 AgentProfile。
- 不一次性实现多 Agent 协商。

### TASK-030: ModelRoute

目标：拆分 Provider / Model / Credential / Route，并让 StageRuntime 通过 ModelRouter 解析模型。

完成状态：已落地 `src/agent_forge/llm/router.py`、`src/agent_forge/models/llm.py`、`016_llm_model_routes.py`、结构化 `/api/v1/llm/*`、LLM 设置页、StageRuntime model route 追踪和非敏感 prompt 上下文。

不做：

- 不在 API 响应或日志中输出明文 API Key。
- 不强制所有用户立即配置多供应商。

### TASK-031: Skill Runtime 闭环

目标：外部 Skill 导入必须经过 Manifest、权限、注册、调用、审计。

完成状态：已落地 `src/agent_forge/skills/manifest.py`、`runtime_spec.py`、`policy.py`、`017_skill_runtime_policy.py`、`/api/v1/skills/import/preview`、`/api/v1/skills/import/install`、前端导入预览和 SkillDispatcher 权限审计。

不做：

- 不默认允许任意第三方 Skill 执行本地命令。
- 不把市场展示等同于运行时可用。
- 不在本任务完成 Stage 级 Skill 策略编排和统一人工确认策略。

### TASK-032: GovernancePolicy

目标：统一阶段确认、技术选型确认、影响范围确认、写回确认和高风险 Skill 调用确认。

完成状态：已落地 `src/agent_forge/governance/policy.py`、`018_governance_confirmation_context.py`、Pipeline confirmation 上下文、Delivery 未确认拒绝上下文、高风险 Skill 调用治理审计和 ConfirmCard 策略结果渲染。

不做：

- 不取消现有 confirmation API。
- 不让前端独立判断核心风险策略。

### TASK-033: EvalFeedback

目标：记录 Pipeline / Stage / Agent / Model / Skill / Artifact / Delivery 维度的执行事实。

完成状态：已落地 `EvalEvent`、`EvaluationService`、`019_eval_events.py`、`/api/v1/evaluation/summary`、Dashboard evaluation 指标、`eval_events` / `evaluation` 导出，以及 StageRuntime、SkillDispatcher、Pipeline 确认和 Delivery 的非阻塞事件记录。

不做：

- 不在第一版实现复杂自动评分。
- 不让 Eval 写入失败阻断主链路。

### TASK-034: 文档收敛

目标：把 AI Runtime 实现结果同步到 architecture、tech-design、MEMORY 和 CLAUDE。

完成状态：已更新 Agent 模型、核心开发闭环、AI Runtime 主线、ARCHITECTURE、LLM-CONFIG、API-SPEC、DATABASE、SECURITY、DATA-EXPORT、docs README、MEMORY、CLAUDE，并新增 `ITERATION-REVIEW.md`。

不做：

- 不删除历史文档。
- 不把未实现能力写成已实现能力。

## 8. 当前风险

| 风险 | 表现 | 对应任务 |
|------|------|----------|
| 阶段语义漂移 | 已通过后端 Pipeline Catalog 收敛，后续需保持前端只读 Catalog | TASK-034 |
| Agent 配置空转 | AgentProfile 已进入 StageRuntime，AgentSkill allowlist 已参与 Stage 级 SkillPolicy 编排 | 后续增强 |
| 模型配置不可治理 | Provider / Model / Credential / Route 已落地；后续接入成本和重试治理 | 后续增强 |
| Skill 安全边界不足 | Manifest、权限、风险、Stage 级工具过滤、调用审计和高风险 Governance 决策已落地；MCP 权限归一化可继续增强 | 后续增强 |
| 人工确认逻辑分散 | 阶段、交付和高风险 Skill 已统一到 GovernancePolicy，确认事实已进入 EvalFeedback | 后续增强 |
| 长期优化无数据 | EvalEvent 已记录阶段、Skill、交付、确认和失败事实；LLM token/cost 明细可继续增强 | 后续增强 |
| 文档和代码分叉 | 已通过 TASK-034 建立当前推荐阅读路径；后续架构级变更仍需同步文档 | 持续维护 |

## 9. 完成定义

AI Runtime 收敛完成后，一次执行必须可以回答：

- 这是哪个 Project 下的需求。
- IntentDecision 如何产生。
- 使用了哪个 Pipeline 和 StageDefinition。
- 当前阶段由哪个 AgentProfile 执行。
- 使用了哪个 ModelRoute 和 Credential 引用。
- 可调用哪些 SkillRuntimeSpec，为什么允许。
- 是否经过 GovernanceDecision。
- 生成了哪个 Artifact。
- Delivery 是否成功，失败如何恢复。
- EvalFeedback 记录了哪些质量和成本事实。
