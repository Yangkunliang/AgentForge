# TASK-009 SSE 执行步骤联调验证与风险修正

**日期**：2026-07-07  
**关联任务**：`docs/tasks/TASK-009.md`  
**状态**：自动化验证已补充，待真实浏览器视觉验收

## 背景

TASK-009 已完成后端事件、前端状态层和 UI 组件，但 Phase 4 联调阶段发现两个风险：

1. `sessions.py` 在路由闭包内直接拼装 `execution_steps`，无法单测，也容易与前端事件语义漂移。
2. `code_executor` 同时触发 `tool_call_*` 和 `sandbox_*` 事件，前端和历史消息可能出现“通用工具卡 + 代码执行卡”的重复展示。

## 修正方案

### 1. 提取执行步骤收集器

新增 `agent_forge.api.execution_steps.ExecutionStepCollector`，作为纯状态机消费 SSE 事件并生成 `Message.extra_data`：

- `thinking_start/delta/end` 生成 `ThinkingStep`，开始时 `streaming=true`，结束时写入耗时并关闭 streaming。
- 普通工具调用生成 `ToolCallStep`，`result.error` 或 `success=false` 时标为 `failed`。
- `code_executor` 不生成通用 `ToolCallStep`，只生成 `CodeExecutionStep`。
- 如果代码执行被安全拦截、沙箱繁忙等路径没有 `sandbox_executing`，在 `tool_call_end` 兜底生成失败的 `CodeExecutionStep`。
- `sandbox_timeout` 标记最近的代码执行步骤为 `timeout`，并写入明确错误文案。

### 2. 路由只负责发布和落库

`POST /sessions/{id}/chat` 中的 `sse_publish_and_collect()` 继续按原顺序发布 SSE，同时把事件交给 `ExecutionStepCollector` 收集。任务结束时只读取 `collector.steps` 写入 assistant message 的 `extra_data`。

### 3. 前端避免重复代码执行卡

`useChat.ts` 对 `code_executor` 的处理调整为：

- `tool_call_start`：跳过通用 `ToolCallStep`。
- `sandbox_executing`：创建 `CodeExecutionStep`。
- `sandbox_completed`：先写入 exit code 和耗时。
- `tool_call_end`：补全 stdout/stderr，并在无 `sandbox_executing` 的失败路径兜底创建代码执行步骤。

同时修正 `session.ts` 中 `completeCodeExecution()` 只能更新 `running` 步骤的问题，使 `sandbox_completed` 后到达的 stdout/stderr 仍能补齐到同一张卡片。

## 风险收敛

| 风险 | 修正 |
|------|------|
| 历史消息持久化与实时 UI 结构不一致 | 后端使用同一收集器统一生成 execution_steps |
| code_executor 重复展示两张卡 | 后端和前端都跳过 code_executor 通用 ToolCallStep |
| sandbox_completed 先到导致 stdout/stderr 丢失 | 前端允许补全已 completed 的 CodeExecutionStep |
| 安全拦截/池繁忙没有 sandbox_executing，用户看不到代码执行失败 | 后端与前端都在 tool_call_end 兜底生成失败 CodeExecutionStep |
| 工具失败只显示 completed | `result.error` / `success=false` 标记为 failed |

## 后续验收

仍需用真实浏览器完成视觉验收：

- thinking 到工具卡切换动画。
- 多步骤时间线对齐。
- 移动端 375px 卡片不溢出。
- SSE 中断后的流式气泡 finalize 体验。
