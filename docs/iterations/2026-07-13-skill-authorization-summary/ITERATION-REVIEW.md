# TASK-041 迭代复盘

## 完成内容

- Evaluation summary 新增 `skill_authorizations` 聚合块。
- 聚合支持 required、granted、grant_rate，以及按 Skill / permission 维度拆分。
- 新增回归测试，确保普通 `skill_called` 不会混入授权指标。

## 设计取舍

- 本轮只增强后端 summary，不改 Dashboard UI，避免一次任务跨越服务端聚合和前端展示两条线。
- 排序按 required 降序、granted 降序、名称升序，优先展示频繁触发且被使用过的授权项。
- 不修改 EvalEvent 表结构，继续从 metadata.permissions 读取权限。

## 验证结果

- 红灯验证：新增测试先失败在 `summary["skill_authorizations"]` 缺失。
- 单点转绿：`uv run --extra dev pytest -q tests/api/test_evaluation.py::test_evaluation_service_summarizes_skill_authorizations` 通过。
- 相关回归：`uv run --extra dev pytest -q tests/api/test_evaluation.py tests/api/test_dashboard.py tests/api/test_exports.py`，`16 passed, 9 warnings`。
- 全量后端：`uv run --extra dev pytest -q`，`335 passed, 6 skipped, 11 xfailed, 41 warnings`。
- 前端构建：`cd web && npm run build` 通过，仍有既有 Sass legacy JS API / `@import` deprecation、Rollup pure annotation 和大 chunk 告警。
- 启动验证：`PYTHONPATH=.../src JWT_SECRET_KEY=task041-secret uv run --extra dev uvicorn api.main:app --host 127.0.0.1 --port 18108` 启动到 `Application startup complete`，无启动期异常。
