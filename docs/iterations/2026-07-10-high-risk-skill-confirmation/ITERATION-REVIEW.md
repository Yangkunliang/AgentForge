# TASK-039 迭代复盘

## 完成内容

- Chat API 接收并透传一次性 `skill_authorization`。
- StageRuntime 发现可授权的高风险 Skill 被过滤时发出 `skill_authorization_required` SSE。
- 前端 `useChat` 保存授权请求上下文。
- 新增 `SkillAuthorizationCard`，支持用户授权本阶段并重试。

## 设计取舍

- 本次选择“SSE 提示 + 重试原消息”，避免修改现有阶段确认状态机。
- 授权卡只对 `permission_denied` 展示，不对 `agent_not_allowed` 展示，确保 AgentSkill allowlist 仍是更强边界。
- 授权不持久化，避免用户误以为之后每个阶段都会自动放行高风险 Skill。

## 验证结果

- 红灯验证：目标测试先失败在 `skill_authorization` 未透传和缺少 `skill_authorization_required` 事件。
- 单点转绿：`uv run --extra dev pytest -q tests/api/test_projects.py::test_chat_payload_passes_temporary_skill_authorization tests/pipeline/test_runtime.py::test_stage_runtime_emits_skill_authorization_required_for_bound_high_risk_skill tests/pipeline/test_runtime.py::test_stage_runtime_passes_temporary_high_risk_skill_authorization` 通过。
- 前端构建：`npm run build` 通过；保留既有 Sass deprecated、Rollup pure annotation 和 chunk size warnings。
- 相关回归：`uv run --extra dev pytest -q tests/api/test_projects.py tests/pipeline/test_runtime.py tests/skills/test_policy.py tests/skills/test_builtin_runtime_spec.py`，`22 passed, 13 warnings`。
- 全量后端：`uv run --extra dev pytest -q`，`334 passed, 6 skipped, 11 xfailed, 41 warnings`。
- 启动验证：`PYTHONPATH=.../src JWT_SECRET_KEY=... uv run --extra dev uvicorn api.main:app --host 127.0.0.1 --port 18104` 启动到 `Application startup complete` 后正常关闭；LiteLLM 远程价格表超时后使用本地 fallback，不影响启动。
