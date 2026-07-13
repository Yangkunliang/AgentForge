# TASK-043 测试计划

## 红绿验证

- 新增/调整 Dashboard 测试，要求 helper 来自真实 `api.routes.dashboard`。
- 在收敛旧模块前先运行，确认旧模块不再被测试覆盖。

## 回归验证

- `uv run --extra dev pytest -q tests/api/test_dashboard.py tests/api/test_evaluation.py`
- `uv run --extra dev pytest -q`
- `cd web && npm run build`
- `PYTHONPATH=.../src JWT_SECRET_KEY=... uv run --extra dev uvicorn api.main:app --host 127.0.0.1 --port <port>`
