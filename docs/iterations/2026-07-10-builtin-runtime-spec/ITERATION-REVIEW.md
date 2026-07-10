# TASK-037 迭代复盘

## 完成内容

- 新增 `external_side_effect` 权限，并归类为 high risk。
- 内置 Skill 注册时生成 `source_type=builtin` 的 RuntimeSpec。
- RuntimeSpec 同步写入 Skill DB 和 SkillRegistry。
- 默认 StageSkillPolicy 会过滤 `http_request`、`update_profile`、`code_executor`。

## 设计取舍

- `http_request` 被视作高风险，因为工具本身支持 POST/PUT/PATCH/DELETE，运行前无法只靠 tool schema 保证无副作用。
- `update_profile` 使用 `external_side_effect`，避免误用 `credential` 表达账号状态修改。
- `code_executor` 使用 `shell`，保持高风险治理路径和现有 SkillDispatcher 决策一致。

## 验证结果

- 红灯验证：`uv run --extra dev pytest -q tests/skills/test_builtin_runtime_spec.py` 先失败在 `external_side_effect` 未进入权限模型。
- 单点转绿：同一命令通过，覆盖内置 RuntimeSpec 和默认 StagePolicy 过滤。
- 相关回归：`uv run --extra dev pytest -q tests/skills/test_builtin_runtime_spec.py tests/skills/test_manifest_runtime_spec.py tests/skills/test_policy.py tests/skills/test_dispatcher.py tests/mcp/test_mcp_client.py tests/pipeline/test_runtime.py`，`34 passed, 5 warnings`。
- 全量后端：`uv run --extra dev pytest -q`，`329 passed, 6 skipped, 11 xfailed, 41 warnings`。
- 前端构建：`npm run build` 通过；仅保留既有 Sass deprecated、Rollup pure annotation 和 chunk size warnings。
- 启动验证：`PYTHONPATH=.../src JWT_SECRET_KEY=... uv run --extra dev uvicorn api.main:app --host 127.0.0.1 --port 18102` 启动到 `Application startup complete`；`/api/v1/health` 返回 degraded，原因是本地 DB/RabbitMQ/Redis 未启动，应用启动本身通过。

## 后续任务

- 设计高风险 Skill 临时授权，让用户能在明确确认后让某个阶段使用 `code_executor` 或 `http_request`。
- 可继续拆分 `http_request` 为只读工具和写操作工具，降低默认隐藏带来的可用性损失。
