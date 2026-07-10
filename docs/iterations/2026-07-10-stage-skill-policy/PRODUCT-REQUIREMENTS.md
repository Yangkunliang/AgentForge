# Stage 级 SkillPolicy 编排需求

## 1. 背景

TASK-027～TASK-034 已把 AgentForge 的 AI Runtime 收敛到 `Project -> Intent -> Pipeline -> Stage -> Agent/Profile -> Skill Runtime -> Artifact -> Delivery -> Eval Feedback`。其中 `StageDefinition.skill_policy_key` 和 `AgentProfile.allowed_skill_names` 已进入架构契约，但 TASK-034 前仍只是可追溯字段，尚未在 LLM 可见工具列表上生效。

本任务让阶段策略和 Agent 绑定的 Skill 在运行时真正决定每个阶段可调用哪些工具，减少“所有工具都给模型看，再等调用时拒绝”的风险。

## 2. 用户故事

作为全栈开发工程师，我希望 AgentForge 在不同阶段只暴露当前阶段和当前 Agent 被允许使用的 Skill，避免无关或高风险工具进入模型可选工具列表。

## 3. 范围

- AgentResolver 从 `agent_skills` 读取已启用 Skill，生成 `AgentProfile.allowed_skill_names`。
- SkillPolicy 根据 `StageDefinition.skill_policy_key`、SkillRuntimeSpec permissions 和 AgentProfile allowlist 过滤 tool_defs。
- StageRuntime 在调用 SkillExecutionEngine 前过滤 tools，并把过滤报告写入 runtime context。
- 保留 SkillDispatcher 调用前权限校验作为第二道防线。

## 4. 非目标

- 不新增数据库表或迁移。
- 不做前端 Agent-Skill 绑定管理页面。
- 不实现用户确认后临时解锁高风险 Skill。
- 不归一化所有 MCP Tool 权限；MCP adapter 留作后续增强。

## 5. 验收

- StageRuntime 传给 SkillExecutionEngine 的 tools 已被阶段策略和 Agent allowlist 过滤。
- 默认策略只允许 `network` 和 `project_context` 权限的结构化 Skill，对 `shell`、`filesystem`、`credential` 不主动暴露给 LLM。
- Agent 绑定了 Skill 时，只暴露绑定且启用的 Skill。
- 过滤报告进入 `advanced_context.skill_policy`，可被后续 Eval 或调试使用。
