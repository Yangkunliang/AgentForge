# Stage 级 SkillPolicy 任务清单

| 任务 | 标题 | 模块 | 优先级 | 状态 |
|------|------|------|--------|------|
| TASK-035 | Stage 级 SkillPolicy 编排 | skills, pipeline, agents | P1 | done |

## Checklist

- [x] 新增 SkillPolicy 过滤单测，覆盖阶段权限和 Agent allowlist。
- [x] 新增 StageRuntime 集成测试，覆盖 engine 收到过滤后的 tools。
- [x] AgentResolver 从 `agent_skills` 生成 `AgentProfile.allowed_skill_names`。
- [x] SkillPolicy 新增 `filter_tool_defs_for_runtime()` 和过滤报告。
- [x] StageRuntime 在调用 SkillExecutionEngine 前过滤 tools。
- [x] 同步架构、API、安全和索引文档。
- [x] 运行后端目标测试、全量 pytest、前端 build 和 FastAPI 启动验证。

## 后续

- MCP Tool 权限归一化。
- 用户确认后临时解锁高风险 Skill。
- 前端 Agent-Skill 绑定管理。
