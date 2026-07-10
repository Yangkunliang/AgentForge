# TASK-039 测试计划

## 后端

- `test_chat_payload_passes_temporary_skill_authorization`
  - 验证 chat payload 的 `skill_authorization` 会进入 `advanced_context`。
- `test_stage_runtime_emits_skill_authorization_required_for_bound_high_risk_skill`
  - 验证 Agent 已绑定但 StagePolicy 拒绝的高风险 Skill 会触发 SSE 授权请求。

## 前端

- `npm run build`
  - 验证类型、Vue 模板和生产构建。

## 回归

- `uv run --extra dev pytest -q tests/api/test_projects.py tests/pipeline/test_runtime.py tests/skills/test_policy.py tests/skills/test_builtin_runtime_spec.py`
- 全量后端 pytest。
- FastAPI uvicorn 启动验证。
