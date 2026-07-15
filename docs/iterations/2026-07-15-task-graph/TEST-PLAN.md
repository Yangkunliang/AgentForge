# TASK-049 测试计划

## 红绿矩阵

1. 输出契约
   - Catalog 和 StageExecutionContext 暴露 `task_graph_v1`。
   - system prompt 包含严格 JSON 字段和“不得输出 Markdown fence”。

2. 解析与校验
   - 合法 DAG 通过。
   - 非 JSON、重复 key、未知依赖、自依赖、环和不安全路径失败。

3. 持久化
   - Graph、Node、Dependency 与 source Artifact 同一事务创建。
   - Artifact Markdown 可读并包含 `task_graph_id` provenance。

4. Runtime
   - task_split 合法输出完成阶段并创建图。
   - 非法输出使 Stage/PipelineRun failed，且无 Artifact/TaskGraph。

5. API 隔离
   - 所属用户读取 200。
   - 其他用户读取 404。

## 回归命令

```bash
uv run --extra dev pytest -q tests/pipeline/test_task_graph.py tests/pipeline/test_runtime.py tests/api/test_pipeline_catalog.py tests/api/test_pipeline_runs.py tests/skills/test_engine_context.py
uv run --extra dev pytest -q
```

## 启动与迁移验证

```bash
uv run alembic -c migrations/alembic.ini heads
PYTHONPATH=src JWT_SECRET_KEY=test-secret .venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port 18149
```
