# TASK-038 技术设计

## 运行时契约

高风险 Skill 临时授权通过 `advanced_context.skill_authorization` 传入 StageRuntime：

```json
{
  "skill_authorization": {
    "authorized_skill_names": ["code-executor"],
    "authorized_permissions": ["shell"],
    "source": "user_confirmation"
  }
}
```

字段说明：

| 字段 | 说明 |
|------|------|
| `authorized_skill_names` | 当前阶段临时允许的 Skill 名称，推荐使用的最小授权粒度。 |
| `authorized_permissions` | 当前阶段临时允许的权限标签，主要用于审计和兼容权限级授权。 |
| `source` | 授权来源，当前运行时保留在上游上下文中，后续 UI/API 可使用 `user_confirmation`。 |

## 过滤顺序

`filter_tool_defs_for_runtime()` 的顺序保持安全优先：

1. `policy.disabled` 直接拒绝。
2. `AgentProfile.allowed_skill_names` 先限制 Agent 可见 Skill。
3. 未注册工具按 StagePolicy 处理。
4. `SkillRuntimeSpec.permissions` 与 `StageSkillPolicy.allowed_permissions` 比对。
5. 仅当被拒权限全部在 `authorized_permissions` 内，或 Skill 命中 `authorized_skill_names` 时，本阶段临时放行。

这意味着临时授权不会越过 Agent 绑定范围，也不会改变默认 StagePolicy。

## 报告上下文

`SkillToolFilterReport.to_context()` 新增：

```json
{
  "authorized_skill_names": ["code-executor"],
  "authorized_permissions": ["shell"]
}
```

该信息会进入 `advanced_context.skill_policy`，用于后续 Prompt 上下文、调试、审计和评估。

## 代码变更

| 文件 | 变更 |
|------|------|
| `src/agent_forge/skills/policy.py` | 增加授权参数、授权报告和权限归一化。 |
| `src/agent_forge/pipeline/runtime.py` | 从 `advanced_context.skill_authorization` 读取授权并传给 SkillPolicy。 |
| `tests/skills/test_policy.py` | 覆盖临时授权和 Agent allowlist 不可绕过。 |
| `tests/pipeline/test_runtime.py` | 覆盖 StageRuntime 透传授权后高风险工具进入 engine tools。 |

## 后续接入点

- API 层可在确认接口或 chat 请求中生成 `skill_authorization`。
- 前端可在高风险 Skill 卡片上展示授权范围，让用户确认后仅重试当前阶段。
- EvalEvent 可继续记录 `authorized_skill_names`，支持“高风险授权频率”指标。
