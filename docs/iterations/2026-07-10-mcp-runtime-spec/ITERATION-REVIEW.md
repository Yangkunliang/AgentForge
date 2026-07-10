# TASK-036 迭代复盘

## 完成内容

- MCP 配置新增权限声明，并复用 `normalize_permissions()`。
- 未声明权限的 MCP Server 默认标记为 `credential` 高风险。
- MCP 注册 SkillRegistry 时写入 `source_type=mcp` 的 RuntimeSpec。
- StageSkillPolicy 可基于 MCP RuntimeSpec 过滤高风险 MCP 工具。

## 设计取舍

- 默认高风险优先于兼容性：第三方 MCP 的实际能力无法仅从协议自动判断，未声明权限时不应默认暴露给 LLM。
- MCP 仍复用 SkillRegistry：避免给外部工具单独开一套权限和审计模型。
- `manifest_hash` 采用配置和 tool names 的稳定 hash：不伪造 MCP manifest，但保留变更追踪能力。

## 验证结果

- 红灯验证：`uv run --extra dev pytest -q tests/mcp/test_mcp_client.py` 先失败在 `MCPServerConfig.permissions` 缺失、MCP RuntimeSpec 缺失；直接构造重复 permissions 的单点测试也先失败。
- 相关回归：`uv run --extra dev pytest -q tests/mcp/test_mcp_client.py tests/skills/test_policy.py tests/skills/test_dispatcher.py tests/pipeline/test_runtime.py`，`29 passed, 5 warnings`。
- 全量后端：`uv run --extra dev pytest -q`，`328 passed, 6 skipped, 11 xfailed, 41 warnings`。
- 前端构建：`npm run build` 通过；仅保留既有 Sass deprecated、Rollup pure annotation 和 chunk size warnings。
- 启动验证：`PYTHONPATH=.../src JWT_SECRET_KEY=... uv run --extra dev uvicorn api.main:app --host 127.0.0.1 --port 18101` 启动到 `Application startup complete`；`/api/v1/health` 返回 degraded，原因是本地 DB/RabbitMQ/Redis 未启动，应用启动本身通过。

## 后续任务

- 将内置 Skill 注册也补齐 RuntimeSpec，继续缩小未声明权限工具面。
- MCP 管理 UI 后续应展示权限声明状态，并引导用户按最小权限配置。
