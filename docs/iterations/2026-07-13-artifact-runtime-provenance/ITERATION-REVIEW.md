# TASK-044 迭代复盘

## 完成内容

- Artifact metadata 新增 `runtime` 子对象，用于固化阶段产物的生成来源。
- StageRuntime 将已解析的 AgentProfile、ModelRoute、model name 和 SkillPolicy 写入 Artifact。
- Artifact 详情页展示 Agent、模型和路由，历史产物没有 runtime metadata 时保持原样。

## 红绿测试

- 红灯：`tests/pipeline/test_runtime.py::test_stage_runtime_creates_artifact_for_completed_stage` 失败在缺少 `runtime`。
- 绿灯：同一测试通过。

## 验证结果

- 相关回归：`uv run --extra dev pytest -q tests/pipeline/test_runtime.py tests/api/test_projects.py tests/api/test_evaluation.py`，`22 passed, 13 warnings`。
- 后端全量：`uv run --extra dev pytest -q`，`337 passed, 6 skipped, 11 xfailed, 41 warnings`。
- 前端构建：`npm run build` 通过，仍有既有 Sass legacy API / `@import`、Rollup pure annotation 和 chunk size 警告。
- FastAPI 启动：`PYTHONPATH=.../src JWT_SECRET_KEY=... uv run --extra dev uvicorn api.main:app --host 127.0.0.1 --port 18114` 到达 `Application startup complete`。
- 本次 `npm install` 仍提示 `2 vulnerabilities (1 moderate, 1 high)`，未执行破坏性 `npm audit fix --force`。

## 后续建议

- 如果后续需要按产物来源做筛选或报表，再把核心 provenance 从 metadata 提升为结构化字段或关联表。
- 可继续把 LLM token / cost 明细接入 EvalEvent，并在 Artifact 详情页展示成本摘要。
