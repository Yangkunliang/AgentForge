# TASK-038 高风险 Skill 临时授权

## 背景

TASK-035 到 TASK-037 已经把内置 Skill、第三方 Skill 和 MCP tool 都纳入 `SkillRuntimeSpec` 权限模型。默认阶段只暴露 `network` 和 `project_context` 权限工具，因此 `code_executor`、`http_request` 写操作和其他高风险 Skill 不会主动出现在 LLM tools 中。

这保证了安全性，但也带来一个真实产品问题：当全栈开发工程师明确需要“运行一次测试命令”“调用一次外部写接口”时，平台需要有一个可审计、可恢复、不会变成长期放权的临时授权机制。

## 目标

- 用户确认后，当前阶段可以临时使用指定高风险 Skill。
- 授权只作用于本次 StageRuntime 调用，不写入 Agent 或全局 StagePolicy。
- Agent 未绑定的 Skill 不能被临时授权绕过。
- 运行时上下文必须记录本次授权范围，方便后续审计、UI 展示和 Eval 分析。

## 非目标

- 不在本任务实现完整前端授权弹窗。
- 不新增数据库表。
- 不改变 `SkillDispatcher` 调用前权限校验的第二道防线。
- 不默认开放 `shell`、`filesystem`、`credential`、`external_side_effect`。

## 用户故事

- 作为全栈开发工程师，我希望在“修复 bug”阶段明确确认后，允许 Agent 使用一次 `code_executor` 跑测试，而不是永久开启代码执行能力。
- 作为团队成员，我希望授权粒度可以指向具体 Skill，避免“一次确认 shell 权限”导致所有 shell 类 Skill 都可见。
- 作为平台管理员，我希望运行时能留下授权范围，让后续日志、审计和评估可追溯。

## 验收标准

- 默认 StageSkillPolicy 仍会过滤高风险 Skill。
- 当 `advanced_context.skill_authorization.authorized_skill_names` 包含目标 Skill 时，目标 Skill 可在当前阶段进入 LLM tools。
- 当 AgentProfile 未绑定某个 Skill 时，即使授权也不能暴露该 Skill。
- `advanced_context.skill_policy` 中包含 `authorized_skill_names` 和 `authorized_permissions`。
