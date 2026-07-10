# Stage 级 SkillPolicy 迭代复盘

```yaml
task: TASK-035
status: completed
completed_at: 2026-07-10
```

## 完成内容

- `AgentResolver` 读取 `agent_skills`，把已启用绑定写入 `AgentProfile.allowed_skill_names`。
- `SkillPolicy` 新增阶段级工具过滤和结构化过滤报告。
- `StageRuntime` 在调用 `SkillExecutionEngine` 前过滤 `tools`，并把 `skill_policy` report 注入 runtime context。
- 保留 `SkillDispatcher` 调用前权限校验，形成“LLM 可见工具过滤 + 实际调用二次校验”的双层治理。

## 验证

- 新增红绿测试：`tests/skills/test_policy.py`。
- 新增 StageRuntime 集成测试：`test_stage_runtime_filters_tools_by_stage_policy_and_agent_allowed_skills`。
- 后续合并前需完成全量 pytest、前端 build 和 FastAPI 启动验证。

## 后续建议

- 继续推进 MCP RuntimeSpec adapter，让 MCP Tool 也具备统一 permissions。
- 增加前端 Agent-Skill 绑定管理入口。
- 设计人工确认后临时解锁高风险 Skill 的短期授权机制。
