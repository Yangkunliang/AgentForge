# TASK-038 迭代复盘

## 完成内容

- `filter_tool_defs_for_runtime()` 支持阶段级临时授权。
- `StageRuntime` 从 `advanced_context.skill_authorization` 读取授权范围。
- `SkillToolFilterReport` 输出授权 Skill 和权限，供运行时上下文追踪。
- 测试覆盖“已绑定且已授权可放行”和“未绑定不能绕过”两个关键安全边界。

## 设计取舍

- 本任务只实现运行时契约，不做 UI/API 完整闭环，避免一次迭代同时改聊天交互、确认接口和安全策略。
- Agent allowlist 优先于临时授权，保证用户确认只是在当前 Agent 能力范围内放松权限，而不是跨 Agent 授权。
- `authorized_skill_names` 是推荐方式；`authorized_permissions` 保留给更高层策略和审计，但后续 UI 应优先引导用户确认具体 Skill。

## 验证结果

- 红灯验证：`uv run --extra dev pytest -q tests/skills/test_policy.py tests/pipeline/test_runtime.py` 先失败在缺少授权参数和 StageRuntime 未透传。
- 单点转绿：`uv run --extra dev pytest -q tests/skills/test_policy.py tests/pipeline/test_runtime.py tests/skills/test_builtin_runtime_spec.py` 已通过。
- 全量后端：`uv run --extra dev pytest -q`，`332 passed, 6 skipped, 11 xfailed, 41 warnings`。
- 前端构建：`npm run build` 通过；保留既有 Sass deprecated、Rollup pure annotation 和 chunk size warnings。
- 启动验证：`PYTHONPATH=.../src JWT_SECRET_KEY=... uv run --extra dev uvicorn api.main:app --host 127.0.0.1 --port 18103` 启动到 `Application startup complete` 后正常关闭。

## 后续任务

- 增加高风险 Skill 授权 UI/API，让用户能从 ConfirmCard 或工具风险提示中确认并重试当前阶段。
- 将授权事实写入 EvalEvent，形成高风险授权频率、失败率和用户撤销率指标。
- 评估把 `http_request` 拆成只读 GET 和写操作工具，减少对高风险授权的依赖。
