# TASK-042 测试计划

## 红绿验证

- 新增 Dashboard 后端测试，先断言 `evaluation.skill_authorizations` 存在并包含 Skill / permission 聚合，确认红灯失败。
- 实现后重跑同一测试转绿。

## 回归验证

- `uv run --extra dev pytest -q tests/api/test_dashboard.py tests/api/test_evaluation.py`
- `cd web && npm run build`

## 完整验证

- `uv run --extra dev pytest -q`
- `cd web && npm run build`
- `PYTHONPATH=.../src JWT_SECRET_KEY=... uv run --extra dev uvicorn api.main:app --host 127.0.0.1 --port <port>`
