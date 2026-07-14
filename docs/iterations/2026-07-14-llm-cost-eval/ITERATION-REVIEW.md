# TASK-045 迭代复盘

## 完成内容

- SkillExecutionEngine 在 `tool_use_complete` 成功返回后记录 `llm_tool_use_completed` EvalEvent。
- 事件带上 Project、PipelineRun、Stage、AgentProfile、ModelRoute、model name、token、成本和耗时。
- Evaluation summary 新增 `llm` 聚合块，并让 Agent / ModelRoute 维度包含 `tokens_used`。
- 明确流式 `stream_complete` token / cost 仍是后续增强。

## 红绿测试

- 红灯：`tests/skills/test_engine_context.py::test_skill_engine_records_llm_tool_use_usage_event` 失败于构造参数缺失。
- 红灯：`tests/api/test_evaluation.py::test_evaluation_service_summarizes_llm_usage` 失败于 summary 缺少 `llm`。
- 绿灯：上述两个测试通过。

## 验证结果

- 相关回归：`uv run --extra dev pytest -q tests/skills/test_engine_context.py tests/api/test_evaluation.py tests/pipeline/test_runtime.py`，`18 passed, 13 warnings`。
- 后端全量：`uv run --extra dev pytest -q`，`339 passed, 6 skipped, 11 xfailed, 41 warnings`。
- 前端构建：`npm run build` 通过，仍有既有 Sass legacy API / `@import`、Rollup pure annotation 和 chunk size 警告。
- FastAPI 启动：sandbox 下 `uv run` 触发用户级 uv cache 权限限制；改用当前 `.venv/bin/python -m uvicorn api.main:app` 后，应用生命周期到达 `Application startup complete`，随后 sandbox 禁止绑定 `127.0.0.1:18145` 导致进程退出。
- 本次 `npm install` 仍提示 `2 vulnerabilities (1 moderate, 1 high)`，未执行破坏性 `npm audit fix --force`。

## 后续建议

- 接入 `stream_complete` usage 统计前，需要先确认 LiteLLM 流式响应中 usage 的稳定来源。
- Dashboard 可新增 LLM 成本趋势、按 Stage / ModelRoute 的 token 成本排行。
- `budget_policy` 可在后续进入 GovernancePolicy，实现超预算确认或拦截。
