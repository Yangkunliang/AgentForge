# TASK-043 迭代复盘

## 完成内容

- `tests/api/test_dashboard.py` 改为从真实 `api.routes.dashboard` 导入 helper。
- `src/agent_forge/api/routes/dashboard.py` 改为兼容 re-export，不再维护第二份 Dashboard 实现。
- 新增测试锁定旧模块 `router` 和 `_get_evaluation_stats` 必须指向真实模块对象。
- 修正真实 Dashboard `_agent_stats()`：inactive Agent 不再固定为 0。

## 验证结果

- 红灯验证：`uv run --extra dev pytest -q tests/api/test_dashboard.py::test_legacy_dashboard_module_reexports_runtime_dashboard` 先失败在旧模块 `router` 与真实模块不是同一对象。
- 单点转绿：同一条测试通过。
- 相关回归：`uv run --extra dev pytest -q tests/api/test_dashboard.py tests/api/test_evaluation.py`，`12 passed, 9 warnings`。
- 全量后端：`uv run --extra dev pytest -q`，`337 passed, 6 skipped, 11 xfailed, 41 warnings`。
- 前端构建：`cd web && npm run build` 通过，仍有既有 Sass legacy JS API / `@import` deprecation、Rollup pure annotation 和大 chunk 告警。
- 启动验证：`PYTHONPATH=.../src JWT_SECRET_KEY=task043-secret uv run --extra dev uvicorn api.main:app --host 127.0.0.1 --port 18112` 启动到 `Application startup complete`，无启动期异常。
