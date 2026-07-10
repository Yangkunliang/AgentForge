# TASK-039 技术设计

## 后端

`ChatRequest` 新增：

```json
{
  "skill_authorization": {
    "authorized_skill_names": ["code-executor"],
    "authorized_permissions": ["shell"],
    "source": "user_confirmation"
  }
}
```

`_build_advanced_context()` 只在授权 Skill 或权限非空时写入 `advanced_context.skill_authorization`，避免空授权污染运行时。

StageRuntime 在 `filter_tool_defs_for_runtime()` 之后检查 `SkillToolFilterReport.excluded_tools`：

- 只对 `reason=permission_denied` 的项发授权事件。
- `agent_not_allowed` 不发授权事件，避免提示用户授权当前 Agent 不具备的 Skill。
- 事件 payload 不包含用户消息或源码内容。

SSE 事件：

```json
{
  "event": "skill_authorization_required",
  "data": {
    "task_id": "task-id",
    "pipeline_run_id": "run-id",
    "stage_id": "locate",
    "skills": [
      {
        "skill_name": "code-executor",
        "tool_name": "code_executor",
        "permissions": ["shell"]
      }
    ]
  }
}
```

## 前端

`useChat()` 监听 `skill_authorization_required`，保存：

- 原 sessionId
- 原用户消息
- 原高级设置 payload
- 需要授权的 skills

`SkillAuthorizationCard` 渲染在消息区，展示需要授权的 Skill 和权限。用户点击“授权本阶段并重试”时，Chat 页重新调用 `_send()`，在原 payload 上追加：

```ts
skill_authorization: {
  authorized_skill_names,
  authorized_permissions,
  source: 'user_confirmation',
}
```

该授权不进入 `advancedSettings` store，因此不会持久化到 localStorage。

## 风险边界

- 用户点击授权后会产生一条新的用户消息和 assistant 占位，这是当前聊天模型的最小改动；后续可做成“重跑当前阶段”而不追加重复消息。
- 如果授权后仍然失败，SkillDispatcher 的调用前权限校验和 GovernancePolicy 仍保留兜底。
