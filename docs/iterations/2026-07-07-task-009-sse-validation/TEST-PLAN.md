# TASK-009 SSE 执行步骤验证计划

**日期**：2026-07-07  
**范围**：执行步骤状态机、后端落库数据结构、前端代码执行状态补全

## 自动化测试

| 用例 | 覆盖点 | 命令 |
|------|--------|------|
| thinking lifecycle | `thinking_start/delta/end` 串联、streaming 状态关闭、耗时写入 | `uv run --extra dev pytest tests/api/test_execution_steps.py -q` |
| code_executor 单卡 | `tool_call_*` + `sandbox_*` 组合时只生成 `CodeExecutionStep` | 同上 |
| code_executor 无 sandbox 失败 | 安全拦截/池繁忙仍生成 failed `CodeExecutionStep` | 同上 |
| 普通工具失败 | `result.error` 标记 `ToolCallStep.status=failed` | 同上 |
| 多步骤顺序 | thinking → tool_call → thinking 保持事件到达顺序 | 同上 |
| 沙箱超时 | `sandbox_timeout` 标记 timeout 并写入用户可读 stderr | 同上 |

## 构建与启动验证

- 后端全量测试：`uv run --extra dev pytest`
- 前端构建：`cd web && npm run build`
- 后端启动：`PYTHONPATH=src uvicorn api.main:app`

## 手工视觉验收

| 场景 | 验收点 |
|------|--------|
| 纯对话 | 无工具调用时不出现空 ExecutionStepList，正文正常流式 |
| 天气查询 | thinking → weather tool_call → 回复顺序正确 |
| 代码执行成功 | 只出现 CodeExecutionCard，代码、stdout/stderr、耗时齐全 |
| 代码执行失败 | stderr 和 failed/exit_code 状态清晰 |
| SSE 中断 | 气泡退出 streaming 状态，不长期卡住 |
| 375px 移动端 | 时间线、代码块和卡片不横向溢出 |
