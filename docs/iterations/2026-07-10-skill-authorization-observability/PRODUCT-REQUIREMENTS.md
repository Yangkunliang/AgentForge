# TASK-040 产品需求：高风险 Skill 授权可观测性

## 背景

TASK-038 和 TASK-039 已经让高风险 Skill 能够在当前阶段由用户临时授权。下一步需要让平台知道这些授权发生在哪里、哪些 Skill 经常触发、用户确认后是否真正进入运行时。

## 目标

- 记录 `skill_authorization_required` 事实，便于后续分析默认 SkillPolicy 是否过严或过松。
- 记录 `skill_authorization_granted` 事实，确认用户授权已被当前 StageRuntime 使用。
- 事件只写结构化字段，不记录用户消息、源码、文件正文或密钥。

## 非目标

- 不新增持久化授权。
- 不改变 AgentSkill allowlist 的更高优先级。
- 不在本轮实现 Dashboard 新图表。

## 验收标准

- 未授权但已绑定的高风险 Skill 被过滤时，会写入 `EvalEvent.event_type=skill_authorization_required`。
- 用户携带一次性授权重试时，会写入 `EvalEvent.event_type=skill_authorization_granted`。
- EvalEvent metadata 只包含 skill、tool、permissions、policy 以及授权来源等结构化信息。
