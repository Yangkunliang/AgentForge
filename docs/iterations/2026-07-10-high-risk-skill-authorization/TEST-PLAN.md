# TASK-038 测试计划

## 单元测试

| 用例 | 覆盖 |
|------|------|
| `test_filter_tool_defs_accepts_temporary_high_risk_authorization` | Agent 已绑定且授权命中时，高风险 Skill 可临时进入 tools。 |
| `test_temporary_high_risk_authorization_does_not_override_agent_allowlist` | Agent 未绑定时，临时授权不能绕过 allowlist。 |
| `test_stage_runtime_passes_temporary_high_risk_skill_authorization` | StageRuntime 正确读取 `advanced_context.skill_authorization` 并注入过滤报告。 |

## 回归测试

- `tests/skills/test_policy.py`
- `tests/pipeline/test_runtime.py`
- `tests/skills/test_builtin_runtime_spec.py`
- `tests/skills/test_dispatcher.py`

## 完整验证

- 后端全量 pytest。
- 前端 `npm run build`，确保类型和构建未受运行时契约变更影响。
- FastAPI uvicorn 启动验证，确保新增 helper 不引入启动期错误。
