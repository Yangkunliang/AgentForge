# Stage 级 SkillPolicy 技术设计

## 1. 目标链路

```text
StageDefinition.skill_policy_key
  + AgentProfile.allowed_skill_names
  + SkillRuntimeSpec.permissions
  -> filter_tool_defs_for_runtime()
  -> SkillExecutionEngine.run(tools=filtered_tools)
  -> SkillDispatcher.invoke() 二次权限校验
```

## 2. 模块变更

### 2.1 AgentResolver

`resolve_agent_profile()` 在解析 active Agent 后查询：

```text
AgentSkill.agent_id == agent.id
AgentSkill.enabled == true
Skill.enabled == true
```

并按 Skill name 升序写入 `AgentProfile.allowed_skill_names`。若 Agent 没有绑定 Skill，则返回空列表，表示没有显式 Agent allowlist 限制。

### 2.2 SkillPolicy

新增：

- `StageSkillPolicy`
- `SkillToolFilterReport`
- `resolve_stage_skill_policy()`
- `filter_tool_defs_for_runtime()`

默认策略：

| policy_key | 行为 |
|------------|------|
| `default` | 允许 `network`、`project_context`；未声明 runtime_spec 的内置工具保持可见；高风险权限不主动暴露 |
| `no_tools` | 不暴露任何工具 |

过滤顺序：

1. `policy.disabled` 时全部排除。
2. Agent allowlist 非空时，排除不在 allowlist 中的 Skill。
3. policy 不允许未注册工具时，排除未注册工具。
4. 排除权限超出 policy.allowed_permissions 的工具。

### 2.3 StageRuntime

StageRuntime 在 `_start_current_stage()` 得到 StageDefinition 后返回 `skill_policy_key`。调用 SkillExecutionEngine 前使用 `filter_tool_defs_for_runtime()` 得到 `effective_tools` 和 report：

```text
SkillExecutionEngine.run(tools=effective_tools)
advanced_context.skill_policy = report.to_context()
```

这保证 LLM tool_use 选择面先被收窄，SkillDispatcher 的权限校验继续作为调用前第二道防线。

## 3. 风险与处理

| 风险 | 处理 |
|------|------|
| 现有内置 Skill 没有 runtime_spec | 默认允许未声明 runtime_spec 的工具，避免破坏内置工具 |
| Agent 未绑定 Skill 后工具全空 | 空 allowlist 表示没有显式 Agent 限制，仍按 stage policy 过滤 |
| 高风险 Skill 完全不可见 | 当前默认策略主动隐藏高风险工具，后续可加人工确认后临时解锁 |
| MCP Tool 权限缺失 | 暂按未注册/未声明处理，MCP RuntimeSpec adapter 后续补齐 |

## 4. 测试

- `tests/skills/test_policy.py`：验证 policy 过滤权限和 Agent allowlist。
- `tests/pipeline/test_runtime.py`：验证 StageRuntime 传入 engine 的 tools 已过滤，并带过滤报告。
