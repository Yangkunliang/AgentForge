# TASK-040 迭代复盘

## 完成内容

- `SkillToolFilterReport` 新增 `authorized_tools`，记录被一次性授权放行的 Tool。
- StageRuntime 对可授权但被过滤的高风险 Skill 写入 `skill_authorization_required` EvalEvent。
- StageRuntime 对已使用的一次性授权写入 `skill_authorization_granted` EvalEvent。
- EvalEvent metadata 只记录权限、策略、授权来源等结构化信息，不记录用户消息、源码或凭据。

## 设计取舍

- 本轮只做 EvalEvent 可观测性，不新增 AuditLog 事件，避免把同一事实写入两套强审计渠道。
- 事件按 Tool 粒度写入，后续 Dashboard 可以按 Skill、权限、阶段聚合。
- `agent_not_allowed` 仍不进入授权事件，保持 AgentSkill allowlist 的更高优先级。

## 验证结果

- 红灯验证：新增两条 StageRuntime 测试先失败在找不到 `skill_authorization_required` / `skill_authorization_granted` EvalEvent。
- 单点转绿：`uv run --extra dev pytest -q tests/pipeline/test_runtime.py::test_stage_runtime_passes_temporary_high_risk_skill_authorization tests/pipeline/test_runtime.py::test_stage_runtime_emits_skill_authorization_required_for_bound_high_risk_skill` 通过。
- 相关回归：`uv run --extra dev pytest -q tests/pipeline/test_runtime.py tests/skills/test_policy.py tests/api/test_evaluation.py`，`14 passed, 13 warnings`。
- 全量后端：`uv run --extra dev pytest -q`，`334 passed, 6 skipped, 11 xfailed, 41 warnings`。
- 前端构建：`npm run build` 通过；新 worktree 缺依赖时先执行 `npm install`，npm audit 仍报告 1 moderate + 1 high，未执行破坏性 `audit fix --force`。
- 启动验证：`PYTHONPATH=.../src JWT_SECRET_KEY=... uv run --extra dev uvicorn api.main:app --host 127.0.0.1 --port 18106` 启动到 `Application startup complete` 后正常关闭；LiteLLM 远程价格表超时后使用本地 fallback，不影响启动。
