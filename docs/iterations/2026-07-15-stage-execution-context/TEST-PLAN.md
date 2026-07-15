# TASK-047 测试计划

## 红绿测试

1. `tests/api/test_pipeline_catalog.py`
   - Catalog API 暴露 `required_input_artifact_types` 和 `success_criteria`。
   - 断言开发阶段消费前序设计产物，测试阶段声明代码输入。

2. `tests/pipeline/test_execution_context.py`
   - 同 Run 前序 Artifact 被加载。
   - 其他 Run、其他 Project、当前阶段和未来阶段 Artifact 被排除。
   - 单项 4000、总计 12000、最多 6 项限制生效。
   - 同一阶段同类型的多次修订只选择最新 Artifact。
   - 缺失必需类型被稳定返回。

3. `tests/pipeline/test_runtime.py`
   - StageRuntime 将 `stage_execution` 传给 FakeSkillEngine。
   - Runtime 创建的 Artifact 类型取自 StageDefinition。
   - Artifact 持久化失败时当前 Stage 和 PipelineRun 进入 failed。

4. `tests/skills/test_engine_context.py`
   - system prompt 包含阶段目标、输入/输出和完成标准，但不含 Artifact 正文。
   - 上游正文以 untrusted user-level reference 进入 tool-use 和 final prompt。
   - `</upstream_artifact>` 等边界字符被转义。

## 回归命令

```bash
uv run --extra dev pytest -q tests/api/test_pipeline_catalog.py tests/pipeline/test_execution_context.py tests/pipeline/test_runtime.py tests/skills/test_engine_context.py tests/security/test_prompt_injection.py
uv run --extra dev pytest -q
```

## 启动验证

```bash
PYTHONPATH=src JWT_SECRET_KEY=test-secret .venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port 18147
```

日志需到达 `Application startup complete`。若 sandbox 禁止端口绑定，记录生命周期已完成和绑定限制；测试结束后恢复 `test_db.sqlite`。
