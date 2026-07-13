# TASK-044 测试计划

## 红灯

```bash
uv run --extra dev pytest -q tests/pipeline/test_runtime.py::test_stage_runtime_creates_artifact_for_completed_stage
```

预期：新增 `metadata.runtime` 断言后失败，证明 Artifact 当前没有持久化运行来源。

## 单点绿灯

```bash
uv run --extra dev pytest -q tests/pipeline/test_runtime.py::test_stage_runtime_creates_artifact_for_completed_stage
```

预期：StageRuntime 创建 Artifact 后 metadata 包含 runtime provenance。

## 相关回归

```bash
uv run --extra dev pytest -q tests/pipeline/test_runtime.py tests/api/test_projects.py tests/api/test_evaluation.py
```

## 完整验证

```bash
uv run --extra dev pytest -q
cd web && npm run build
PYTHONPATH=.../src JWT_SECRET_KEY=... uv run --extra dev uvicorn api.main:app --host 127.0.0.1 --port <port>
```
