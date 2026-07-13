# TASK-042 迭代复盘

## 完成内容

- `/api/v1/dashboard.evaluation` 新增 `skill_authorizations` 聚合块。
- Dashboard 页面新增「高风险 Skill 授权」卡片，展示请求数、已授权数、通过率、按 Skill 排行和按 permission 排行。
- 前端类型新增 `SkillAuthorizationStats`，并兼容旧后端缺失字段时的 0 值展示。
- 同步 API、架构、索引、MEMORY 和 CLAUDE 文档。

## 设计取舍

- 沿用 `/dashboard` 单 API 数据流，不让前端额外请求 `/evaluation/summary`。
- 本轮只展示前 3 项排行，避免 Dashboard 被长列表挤压。
- 同步旧 `agent_forge.api.routes.dashboard` schema，避免现有测试和兼容导入继续漂移。

## 验证结果

- 红灯验证：`uv run --extra dev pytest -q tests/api/test_dashboard.py::TestDashboardStats::test_runtime_dashboard_evaluation_stats_include_skill_authorizations` 先失败在 `EvaluationStats` 缺少 `skill_authorizations`。
- 单点转绿：同一条测试通过。
- 相关回归：`uv run --extra dev pytest -q tests/api/test_dashboard.py tests/api/test_evaluation.py`，`11 passed, 9 warnings`。
- 前端构建：`cd web && npm run build` 通过，仍有既有 Sass legacy JS API / `@import` deprecation、Rollup pure annotation 和大 chunk 告警。
- 全量后端：`uv run --extra dev pytest -q`，`336 passed, 6 skipped, 11 xfailed, 41 warnings`。
- 启动验证：`PYTHONPATH=.../src JWT_SECRET_KEY=task042-secret uv run --extra dev uvicorn api.main:app --host 127.0.0.1 --port 18110` 启动到 `Application startup complete`，无启动期异常。
