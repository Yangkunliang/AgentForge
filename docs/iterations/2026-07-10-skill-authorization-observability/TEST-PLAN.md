# TASK-040 测试计划

## 自动化测试

- `tests/pipeline/test_runtime.py::test_stage_runtime_records_skill_authorization_required_eval_event`
- `tests/pipeline/test_runtime.py::test_stage_runtime_records_skill_authorization_granted_eval_event`
- `tests/pipeline/test_runtime.py`
- `tests/api/test_evaluation.py`
- 全量 `uv run --extra dev pytest -q`

## 启动与构建

- 后端：`PYTHONPATH=.../src JWT_SECRET_KEY=... uv run --extra dev uvicorn api.main:app`
- 前端：本轮不改前端，最终仍执行 `web && npm run build` 作为合并前回归。

## 重点检查

- EvalEvent 不包含用户消息正文、源码内容或凭据。
- `skill_authorization_required` 只来源于 `permission_denied`。
- `skill_authorization_granted` 只在高风险 Tool 真实进入有效工具集时写入。
