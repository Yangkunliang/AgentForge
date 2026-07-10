# TASK-039 高风险 Skill 授权确认入口

## 背景

TASK-038 已经完成 `advanced_context.skill_authorization` 运行时契约，但用户还没有可点击的确认入口。默认策略会把 `code_executor`、`http_request` 写操作和其他高风险 Skill 从 LLM tools 中过滤掉；如果没有 UI/API 反馈，用户只会看到 Agent 能力不足，而不知道可以明确授权后重试当前阶段。

## 目标

- 后端在当前阶段有已绑定但被权限策略过滤的高风险 Skill 时，通过 SSE 发出授权请求。
- 前端展示授权卡片，列出需要授权的 Skill 和权限。
- 用户点击后，前端使用原消息和一次性 `skill_authorization` payload 重试。
- 授权只作用于本次重试，不进入高级设置持久化，也不改变 Agent 或 StagePolicy。

## 非目标

- 不新增数据库表。
- 不把授权请求做成长期审批流。
- 不改变阶段确认卡的 PRD / 技术设计确认语义。
- 不自动授权未绑定到当前 Agent 的 Skill。

## 验收标准

- `ChatRequest` 支持 `skill_authorization` 字段，并进入 `advanced_context`。
- StageRuntime 对 `permission_denied` 的已注册 Skill 发出 `skill_authorization_required` SSE。
- 前端能显示授权卡片，并在用户确认后重试当前消息。
- `npm run build` 通过。
