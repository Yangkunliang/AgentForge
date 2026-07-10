# TASK-038 Checklist

## 范围

实现高风险 Skill 阶段级临时授权的运行时契约，为后续 UI/API 授权入口打底。

## Checklist

- [x] 梳理 StageRuntime、StageSkillPolicy、AgentSkill allowlist 和 SkillRuntimeSpec 的现有边界。
- [x] 为 SkillPolicy 增加高风险临时授权红灯测试。
- [x] 为 StageRuntime 增加 `advanced_context.skill_authorization` 透传红灯测试。
- [x] 扩展 `filter_tool_defs_for_runtime()`，支持 `authorized_skill_names` 和 `authorized_permissions`。
- [x] 保持 Agent allowlist 优先级高于临时授权。
- [x] 将授权范围写入 `SkillToolFilterReport.to_context()`。
- [x] 同步架构文档、API 说明、安全说明和迭代复盘。
- [ ] 后续任务：实现前端确认 UI 和 API 层授权入口。

## 风险控制

- 临时授权不持久化到 Agent、Skill 或 StageDefinition。
- `authorized_skill_names` 是推荐授权粒度；`authorized_permissions` 只作为运行时上下文补充和兼容入口。
- 未知权限不会被视作授权通过。
