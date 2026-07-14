# TASK-046 测试计划

## TDD 红绿测试

1. `tests/api/test_evaluation.py`
   - 写入同一用户下多个 LLM 事件，覆盖两个 ModelRoute 和两个 Stage。
   - 首次运行应因 summary 缺少 `llm_by_model_route` / `llm_by_stage` 失败。
   - 实现后断言仅聚合 `llm_*` 事件、排序稳定、stage name 可回退。

2. `tests/api/test_dashboard.py`
   - 写入当前用户 LLM 事件。
   - 首次运行应因 `EvaluationStats` 缺少 `llm` 失败。
   - 实现后断言总览字段和前 3 排行契约。

3. `web/e2e/dashboard.spec.ts`
   - Mock Dashboard API 返回完整 LLM 指标。
   - 首次运行应因页面缺少“LLM 实际用量”和指标失败。
   - 实现后断言指标、ModelRoute / Stage 排行和任务费用标签。
   - 第二个场景返回空数组，断言两个零数据状态可见。

## 回归验证

```bash
uv run --extra dev pytest -q tests/api/test_evaluation.py tests/api/test_dashboard.py tests/pipeline/test_runtime.py tests/skills/test_engine_context.py
cd web && npm run build
cd web && npx playwright test e2e/dashboard.spec.ts
```

## 完整验证

```bash
uv run --extra dev pytest -q
cd web && npm run build
PYTHONPATH=src JWT_SECRET_KEY=test-secret .venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port 18147
```

测试结束后恢复 `test_db.sqlite`，确保提交不包含测试数据。
