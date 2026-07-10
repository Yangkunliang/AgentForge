# TASK-037 测试计划

## 单元测试

- `tests/skills/test_builtin_runtime_spec.py`
  - `external_side_effect` 权限可被 normalize，并被归为 high risk。
  - `register_builtin_skills()` 后五个内置 Skill 均有 RuntimeSpec。
  - 默认 StageSkillPolicy 只允许 `web_search` 和 `get_weather`。
  - `http_request`、`update_profile`、`code_executor` 被记录为 `permission_denied`。

## 回归测试

- `tests/skills/test_manifest_runtime_spec.py`
  - 外部 Skill Manifest 权限解析不回退。
- `tests/skills/test_policy.py`
  - 普通 Skill 的 StagePolicy 过滤不回退。
- `tests/skills/test_dispatcher.py`
  - 调用前权限校验和审计不回退。
- `tests/mcp/test_mcp_client.py`
  - MCP RuntimeSpec 权限归一不回退。
- `tests/pipeline/test_runtime.py`
  - StageRuntime 工具过滤不回退。

## 完整验证

- `uv run --extra dev pytest -q`
- `cd web && npm run build`
- `PYTHONPATH=.../src JWT_SECRET_KEY=... uv run --extra dev uvicorn api.main:app --host 127.0.0.1 --port <port>`

## 验收记录

待验证完成后写入 `ITERATION-REVIEW.md`。
