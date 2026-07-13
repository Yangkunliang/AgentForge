# TASK-041 测试计划

## 自动化测试

- `uv run --extra dev pytest -q tests/api/test_evaluation.py::test_evaluation_service_summarizes_skill_authorizations`
- `uv run --extra dev pytest -q tests/api/test_evaluation.py`
- 全量 `uv run --extra dev pytest -q`

## 构建与启动

- `cd web && npm run build`
- `PYTHONPATH=.../src JWT_SECRET_KEY=... uv run --extra dev uvicorn api.main:app`

## 重点检查

- 空数据返回稳定结构。
- 按 Skill 和 permission 聚合时不受无关 EvalEvent 影响。
- 文档描述与 API 返回字段一致。
