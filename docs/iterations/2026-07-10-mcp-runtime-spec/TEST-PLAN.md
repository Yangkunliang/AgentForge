# TASK-036 测试计划

## 单元测试

- `tests/mcp/test_mcp_client.py`
  - MCP 配置默认权限为 `credential`。
  - MCP 配置显式 permissions 会归一化去重。
  - MCP 注册到 SkillRegistry 后包含 RuntimeSpec。
  - `filesystem` MCP tool 在默认 StagePolicy 下被过滤。

## 回归测试

- `tests/skills/test_policy.py`
  - 确认 StageSkillPolicy 仍能按权限和 Agent allowlist 过滤普通 Skill。
- `tests/skills/test_dispatcher.py`
  - 确认调用前权限校验和审计仍保留。
- `tests/pipeline/test_runtime.py`
  - 确认 StageRuntime 过滤工具后再调用 SkillExecutionEngine。

## 完整验证

- `uv run --extra dev pytest -q`
- `cd web && npm run build`
- `JWT_SECRET_KEY=... uv run --extra dev uvicorn api.main:app --host 127.0.0.1 --port <port>` 启动到 `Application startup complete`

## 验收记录

待验证完成后写入 `ITERATION-REVIEW.md`。
