# Stage 级 SkillPolicy 测试计划

## 1. 自动化测试

```bash
uv run --extra dev pytest -q tests/skills/test_policy.py tests/pipeline/test_runtime.py::test_stage_runtime_filters_tools_by_stage_policy_and_agent_allowed_skills
```

目标：验证新增过滤逻辑和 StageRuntime 接入。

```bash
uv run --extra dev pytest -q tests/skills/test_policy.py tests/skills/test_dispatcher.py tests/pipeline/test_runtime.py tests/api/test_pipeline_catalog.py
```

目标：覆盖 SkillPolicy、SkillDispatcher、StageRuntime 和 Pipeline Catalog 回归。

```bash
uv run --extra dev pytest -q
```

目标：后端全量回归。

## 2. 构建与启动

```bash
cd web
npm run build
```

目标：确认前端类型和构建未被文档/API 变更破坏。

```bash
JWT_SECRET_KEY=task035-startup-secret uv run --extra dev uvicorn api.main:app --host 127.0.0.1 --port 18100
```

目标：确认 FastAPI 可启动，启动日志到达 `AgentForge startup complete`。

## 3. 文档检查

```bash
git diff --check
rg -n "TASK-035|filter_tool_defs_for_runtime|Stage 级 SkillPolicy|allowed_skill_names" docs MEMORY.md CLAUDE.md src tests
```
