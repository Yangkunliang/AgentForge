# TASK-009 SSE 执行步骤验证计划

**日期**：2026-07-07  
**范围**：执行步骤状态机、后端落库数据结构、前端代码执行状态补全、浏览器视觉验收

## 自动化测试

| 用例 | 覆盖点 | 命令 |
|------|--------|------|
| thinking lifecycle | `thinking_start/delta/end` 串联、streaming 状态关闭、耗时写入 | `uv run --extra dev pytest tests/api/test_execution_steps.py -q` |
| code_executor 单卡 | `tool_call_*` + `sandbox_*` 组合时只生成 `CodeExecutionStep` | 同上 |
| code_executor 无 sandbox 失败 | 安全拦截/池繁忙仍生成 failed `CodeExecutionStep` | 同上 |
| 普通工具失败 | `result.error` 标记 `ToolCallStep.status=failed` | 同上 |
| 多步骤顺序 | thinking → tool_call → thinking 保持事件到达顺序 | 同上 |
| 沙箱超时 | `sandbox_timeout` 标记 timeout 并写入用户可读 stderr | 同上 |

## 浏览器 E2E 验收

命令：

```bash
cd web
npx playwright test e2e/execution-steps.spec.ts --project=chromium
```

| 场景 | 覆盖点 |
|------|--------|
| 纯对话 | 无工具调用时不出现空 ExecutionStepList，正文正常显示 |
| 天气 + 代码混合步骤 | thinking → get_weather → code_execution 按顺序展示，`code_executor` 不再重复显示为通用工具卡 |
| 历史消息 | 旧 `tool_calls` 格式可读，历史消息不报错 |
| SSE 中断 | 气泡退出 streaming 状态，无流式光标和进度条残留 |
| 运行中反馈 | streaming 场景默认展开，顶部进度条、步骤 spinner、工具卡 spinner 可见 |
| 折叠动画 | CSS transition duration 不超过 300ms，折叠/展开最终状态正确 |
| 时间线对齐 | 多步骤 connector 横向中心一致 |
| 375px 移动端 | 页面无横向滚动，时间线、代码块和卡片不溢出 |

## 构建与启动验证

- 后端全量测试：`uv run --extra dev pytest`
- 前端构建：`cd web && npm run build`
- 后端启动：`PYTHONPATH=src uvicorn api.main:app`

## 验收边界

- 本轮 E2E 使用 dev-only harness 固定消息数据，验证前端渲染、状态和响应式行为。
- 真实 LLM Provider、真实第三方天气服务的网络稳定性不属于本轮浏览器视觉验收范围，后续可在端到端联调环境单独抽验。
