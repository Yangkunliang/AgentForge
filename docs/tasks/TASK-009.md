# TASK-009：SSE 执行过程可视化

**优先级**：P2  
**状态**：Phase 4 自动化验证已补充，待真实浏览器视觉验收
**依赖**：TASK-006（Chat UI）、TASK-008（沙箱执行层）  
**关联设计文档**：[SSE-EXECUTION-VISUALIZATION.md](../tech-design/SSE-EXECUTION-VISUALIZATION.md)  
**关联代码**：`src/agent_forge/api/sse.py`、`src/agent_forge/llm/provider.py`、`src/agent_forge/skills/code_executor.py`、`src/agent_forge/skills/dispatcher.py`、`web/src/`

---

## 背景

当前 SSE 体系后端定义了 17 种事件类型，但前端只消费 5 种，用户在 AI 执行期间看不到任何进度。沙箱代码执行过程完全不可见，工具调用结果以裸 JSON 展示，体验较差。

本任务按四个阶段落地 SSE 执行过程可视化，完成后用户可以实时感知：thinking 进度、工具调用节点、代码执行过程（含代码预览和 stdout/stderr）。

---

## 验收标准

- [ ] thinking 过程通过独立事件流式推送，前端 ThinkingBlock 实时展示文字，结束后自动折叠并显示耗时
- [ ] 工具调用（weather、web_search、http_request 等）展示专属摘要卡片，不再裸 JSON
- [ ] code_executor 有独立 CodeExecutionCard，展示代码块 + 运行中动画 + stdout/stderr 分区
- [ ] 多步骤（thinking → tool_call → thinking → tool_call）顺序正确，按事件到达时序排列
- [ ] 超时、失败等异常状态在卡片内明确展示
- [ ] 旧 `tool_calls` 字段向后兼容（历史消息不报错）

---

## Phase 1：后端事件补齐 ✅

### 1.1 sse.py — 新增事件类型和 emit 函数 ✅
- [x] `SSEEventTypes` 新增：`THINKING_START`、`THINKING_DELTA`、`THINKING_END`、`SANDBOX_EXECUTING`
- [x] 新增 emit 函数：`emit_thinking_start`、`emit_thinking_delta`、`emit_thinking_end`、`emit_sandbox_executing`、`emit_sandbox_completed`、`emit_sandbox_timeout`

### 1.2 llm/provider.py — 流式输出拆分 thinking/response ✅
- [x] `_stream_with_thinking()` 解析两类 thinking 来源：原生 reasoning 字段 + 内嵌 `<thinking>` 标签
- [x] thinking 与正文严格互斥，yield 只输出正文 chunk
- [x] `_suffix_match()` 处理标签被拆断到两个 chunk 的边界情况
- [x] `stream_complete()` 接受可选 thinking 回调参数，不影响现有调用方

### 1.3 skills/dispatcher.py — on_event 注入 ✅
- [x] 检测 Skill 函数签名中是否含 `on_event` 参数，有则动态注入
- [x] 与 `user_id` 注入机制对称，不影响不接受 `on_event` 的 Skill

### 1.4 skills/code_executor.py — 补充沙箱事件 ✅
- [x] 函数签名增加 `on_event: Callable | None = None` 参数
- [x] 执行前 emit `sandbox_executing`（携带完整 code）
- [x] 执行成功后 emit `sandbox_completed`（exit_code + duration_ms）
- [x] 超时时 emit `sandbox_timeout`
- [x] 降级执行（docker/mock）时同样推送事件
- [x] `_emit()` 辅助函数：安全发射，忽略回调异常

### 1.5 skills/engine.py — 接入 thinking 回调 ✅
- [x] `_react_loop` 定义 `_on_thinking_start/delta/end` 回调，转为 `sse_publish` 调用
- [x] 流式最终回复阶段将 thinking 回调传入 `llm.stream_complete()`
- [x] 非流式路径（纯对话、兜底）通过 `_strip_thinking_tags()` 剥离 thinking 标签

---

## Phase 2：数据层 ✅

### 2.1 types/index.ts ✅
- [x] 新增 `ExecutionStep` 联合类型：`ThinkingStep | ToolCallStep | CodeExecutionStep`
- [x] `ChatMessage` 新增 `execution_steps?: ExecutionStep[]`
- [x] 保留 `tool_calls` 字段（`LegacyToolCall`，兼容历史消息）
- [x] 新增 thinking/sandbox/tool_call 相关 `SSEEventType` 枚举值

### 2.2 stores/session.ts ✅
- [x] `startThinkingStep` / `appendThinkingDelta` / `endThinkingStep`
- [x] `startToolCallStep` / `completeToolCallStep` / `failToolCallStep`
- [x] `startCodeExecution` / `completeCodeExecution` / `failCodeExecution`
- [x] `appendToolCall` 保留导出（向后兼容）

### 2.3 composables/useChat.ts ✅
- [x] `thinking_start/delta/end` → sessionStore thinking actions
- [x] `sandbox_executing` → `startCodeExecution`
- [x] `sandbox_completed` → `completeCodeExecution`（耗时）
- [x] `sandbox_timeout` → `failCodeExecution('timeout')`
- [x] `tool_call_start` → `startToolCallStep`（code_executor 走 `startCodeExecution`）
- [x] `tool_call_end` → code_executor 走 `completeCodeExecution`（含完整 stdout/stderr），其他走 `completeToolCallStep`

---

## Phase 3：UI 组件 ✅

### 3.1 ExecutionProgressBar.vue ✅
- [x] indeterminate 进度条，`streaming=true` 时显示
- [x] CSS animation `progress-slide`

### 3.2 ThinkingBlock.vue ✅
- [x] `step: ThinkingStep` prop
- [x] `streaming=true`：spinner + "思考中…"，自动展开
- [x] `streaming=false`：✓ 展示耗时，自动折叠
- [x] `slide` 过渡动画

### 3.3 ToolCallCard.vue ✅
- [x] 工具图标映射（weather/search/http/profile/executor/默认）
- [x] 状态徽章（running/completed/failed/timeout）
- [x] 参数摘要：按工具定制展示，不显示裸 JSON
- [x] 结果摘要：按工具定制展示

### 3.4 CodeExecutionCard.vue ✅
- [x] header：⚡ + 状态 + 耗时 + spinner
- [x] 代码块（超 20 行可折叠）
- [x] running 状态：进度条动画
- [x] completed：stdout（绿色）+ stderr（橙色）+ exit_code 错误区
- [x] failed：错误区（红色）
- [x] timeout：超时提示，不显示代码区

### 3.5 ExecutionStepList.vue ✅
- [x] 外层折叠容器（streaming 展开，全部完成后折叠）
- [x] 步骤数摘要 header
- [x] 时间线连接线（圆点 + 竖线）
- [x] 按步骤类型分发渲染 ThinkingBlock / ToolCallCard / CodeExecutionCard

### 3.6 AssistantMessage.vue ✅
- [x] 引入 `ExecutionProgressBar`（bubble 顶部）
- [x] 引入 `ExecutionStepList`（替换旧 think-block + tool-calls-block）
- [x] 旧 `tool_calls` 数据兜底渲染（`hasLegacyToolCalls`）
- [x] `stripThinkingTags()` 剥离 content 中可能残留的 `<thinking>` 标签
- [x] 移除 `parseThinking()` 依赖（不再需要前端解析标签）

---

## Phase 4：联调验证

### 4.1 核心场景测试
- [ ] **纯对话**：只有 llm_response，无 ExecutionStepList，气泡正常流式
- [ ] **天气查询**：thinking → get_weather tool_call → llm_response，3步顺序正确
- [x] **代码执行**：thinking → code_executor（含代码预览 + 输出）→ llm_response；自动化覆盖 code_executor 单 CodeExecutionStep 与 stdout/stderr 补全
- [x] **多工具穿插**：thinking → tool_call_1 → thinking → tool_call_2，顺序保留；自动化覆盖 execution_steps 按事件到达顺序落库
- [x] **代码执行失败**：CodeExecutionCard 显示 stderr；自动化覆盖无 sandbox 事件的安全拦截失败兜底

### 4.2 异常场景测试
- [x] 代码执行超时（30s）：timeout 状态卡片，整体任务不崩溃；自动化覆盖 `sandbox_timeout` 状态收集
- [x] 工具调用失败：failed 状态卡片，有错误文字；自动化覆盖 `result.error` → failed
- [ ] SSE 中断：streaming 状态正确 finalize
- [ ] 历史消息加载：旧 `tool_calls` 格式不报错，有兜底渲染

### 4.3 视觉验收
- [ ] thinking → tool_call 切换时动画流畅
- [ ] 多步骤时间线连接线对齐
- [ ] 折叠/展开动画 < 300ms
- [ ] 移动端（375px）各卡片不溢出

### 4.4 本轮风险修正与自动化覆盖 ✅
- [x] 抽取 `ExecutionStepCollector`，避免 `sessions.py` 内联收集逻辑不可测试
- [x] 后端持久化跳过 `code_executor` 通用 ToolCallStep，历史消息不再重复展示工具卡和代码卡
- [x] 前端 `tool_call_start/end` 对 `code_executor` 只补全 CodeExecutionStep，不再创建 ToolCallStep
- [x] 修复 `sandbox_completed` 先到后，`tool_call_end` 无法补齐 stdout/stderr 的状态更新问题
- [x] 补充 `tests/api/test_execution_steps.py` 覆盖 thinking、普通工具、code_executor、超时和多步骤顺序

---

## 产出物

| 产出物 | 路径 | 状态 |
|-------|------|------|
| 设计文档 | `docs/tech-design/SSE-EXECUTION-VISUALIZATION.md` | ✅ |
| SSE 事件扩展 | `src/agent_forge/api/sse.py` | ✅ |
| LLM thinking 拆分 | `src/agent_forge/llm/provider.py` | ✅ |
| Dispatcher on_event 注入 | `src/agent_forge/skills/dispatcher.py` | ✅ |
| code_executor 事件发射 | `src/agent_forge/skills/code_executor.py` | ✅ |
| Engine thinking 回调 | `src/agent_forge/skills/engine.py` | ✅ |
| 类型定义 | `web/src/types/index.ts` | ✅ |
| Session Store | `web/src/stores/session.ts` | ✅ |
| useChat 事件处理 | `web/src/composables/useChat.ts` | ✅ |
| 执行步骤收集器 | `src/agent_forge/api/execution_steps.py` | ✅ |
| 执行步骤回归测试 | `tests/api/test_execution_steps.py` | ✅ |
| ExecutionProgressBar | `web/src/components/chat/ExecutionProgressBar.vue` | ✅ |
| ThinkingBlock | `web/src/components/chat/ThinkingBlock.vue` | ✅ |
| ToolCallCard | `web/src/components/chat/ToolCallCard.vue` | ✅ |
| CodeExecutionCard | `web/src/components/chat/CodeExecutionCard.vue` | ✅ |
| ExecutionStepList | `web/src/components/chat/ExecutionStepList.vue` | ✅ |
| AssistantMessage | `web/src/components/chat/AssistantMessage.vue` | ✅ |

---

## 注意事项

- `parseThinking()` 工具函数已不再被 `AssistantMessage.vue` 使用，可在下次清理时删除
- `thinking_delta` 和 `llm_response` 严格互斥，由 `_stream_with_thinking()` 保证
- `_suffix_match()` 处理跨 chunk 标签拆断问题，覆盖 `<thi`、`</think` 等不完整前缀
- `on_event` 注入到 Skill 时 `_emit()` 辅助函数做了异常守卫，回调失败不影响主流程
- `code_executor` 是代码执行专属卡片，不再作为普通 ToolCallCard 展示；若没有 `sandbox_executing` 事件，`tool_call_end` 会兜底生成失败的 CodeExecutionStep
