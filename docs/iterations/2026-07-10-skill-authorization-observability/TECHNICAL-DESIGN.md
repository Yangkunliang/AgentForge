# TASK-040 技术设计：高风险 Skill 授权可观测性

## 设计原则

- 复用 `EvaluationService.safe_record_event()`，保持主链路非阻塞。
- 事件粒度按 Skill Tool 记录，方便后续聚合到 Skill、权限和阶段。
- 只记录结构化运行事实，避免把用户输入、源码内容或凭据写入 EvalEvent。

## 数据流

```text
StageRuntime
  -> filter_tool_defs_for_runtime()
  -> skill_authorization_required SSE
  -> EvaluationService.safe_record_event(skill_authorization_required)

StageRuntime with advanced_context.skill_authorization
  -> filter_tool_defs_for_runtime()
  -> allowed high-risk tool
  -> EvaluationService.safe_record_event(skill_authorization_granted)
```

## 事件约定

### skill_authorization_required

- `event_type`: `skill_authorization_required`
- `status`: `blocked`
- `skill_name` / `tool_name`: 被过滤的已绑定高风险 Tool。
- `metadata`: `permissions`, `policy_key`, `reason`。

### skill_authorization_granted

- `event_type`: `skill_authorization_granted`
- `status`: `success`
- `skill_name` / `tool_name`: 被当前临时授权放行的 Tool。
- `metadata`: `permissions`, `authorized_skill_names`, `authorized_permissions`, `source`, `policy_key`。

## 边界

- `agent_not_allowed` 不记录为可授权事件。
- 未实际放行的授权 payload 不记录 `granted`。
- 如果 EvalEvent 写入失败，只记录日志，不影响 StageRuntime。
