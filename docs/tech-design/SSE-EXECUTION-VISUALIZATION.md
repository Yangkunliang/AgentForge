# SSE 执行过程可视化设计文档

**文档状态**: 草稿  
**创建日期**: 2026-06-26  
**关联任务**: TASK-009（待创建）  
**依赖文档**: `docs/tech-design/SECURITY.md`, `docs/tech-design/API-SPEC.md`

---

## 一、背景与问题

### 现状

当前 SSE 实现分为两层：

- **后端**：已定义完整的事件体系（`sse.py`），包括 `tool_call_start`、`tool_call_end`、`sandbox_*` 系列等共 17 种事件类型，部分已从 `engine.py` 和 `coder.py` 发射
- **前端**：`useChat.ts` 仅处理 5 种事件（`llm_response`、`tool_call_start`、`tool_call_end`、`task_completed`、`task_failed`），其余全部 `default: break` 静默丢弃
- **UI**：`AssistantMessage.vue` 的工具调用卡片对所有工具用同一个通用样式，code_executor 的 stdout/stderr 以原始 JSON 展示，没有专门渲染

### 问题

用户在等待 AI 执行时，看不到任何进度反馈，体验差：

1. 不知道 AI 在做什么（思考？调用工具？执行代码？）
2. 代码执行过程完全不可见，结果突然出现
3. 工具调用结果以裸 JSON 展示，没有可读性
4. thinking 过程虽然有折叠块，但无法区分"正在思考"和"思考结束"的样式差异

---

## 二、目标

1. 关键执行节点透出给用户，让用户感知进度而非干等
2. 沙箱代码执行过程有专属 UI，代码和输出清晰分离
3. thinking 过程实时流式展示，并与工具执行穿插正确排列
4. 每个阶段有明确的时间反馈
5. 不过度暴露内部实现细节（sandbox_id、host、port 等不展示）

---

## 三、事件层级设计

### 3.1 事件分类

将所有事件分为三类：

| 类型 | 说明 | 展示方式 |
|------|------|---------|
| **用户感知事件** | 需要在 UI 上呈现的节点 | 渲染为可视化组件 |
| **状态辅助事件** | 更新已有组件的状态 | 修改现有组件状态，不新增 |
| **内部事件** | 系统内部实现细节 | 前端静默忽略 |

### 3.2 事件归类表

| 事件名 | 归类 | 前端处理方式 |
|--------|------|------------|
| `task_started` | 状态辅助 | 显示整体进度条开始 |
| `thinking_start` | 用户感知 ⭐ | 展开 thinking 折叠块，开始流式 |
| `thinking_delta` | 用户感知 ⭐ | 向 thinking 块追加文字（新增） |
| `thinking_end` | 状态辅助 | 折叠 thinking 块，标记完成 |
| `tool_call_start` | 用户感知 ⭐ | 普通工具创建工具调用卡片；`code_executor` 不创建通用卡 |
| `tool_call_end` | 用户感知 ⭐ | 普通工具更新卡片状态；`code_executor` 补全代码执行卡 stdout/stderr |
| `sandbox_executing` | 用户感知 ⭐ | 在 code_executor 卡片内展示代码 + loading |
| `sandbox_completed` | 状态辅助 | 更新执行耗时 |
| `sandbox_timeout` | 用户感知 ⭐ | 在卡片内显示超时错误 |
| `llm_response` | 用户感知 ⭐ | 追加到主文本气泡 |
| `task_completed` | 状态辅助 | 标记完成，隐藏进度条 |
| `task_failed` | 用户感知 ⭐ | 显示全局错误提示 |
| `pipeline_started` | 状态辅助 | 更新当前 Session 的 `pipeline_run_id` 并刷新 PipelineRun |
| `stage_started` | 状态辅助 | 刷新 PipelineRun，StagePreview 显示 running/current |
| `stage_completed` | 状态辅助 | 刷新 PipelineRun，StagePreview 推进到下一阶段 |
| `stage_skipped` | 状态辅助 | 刷新 PipelineRun，StagePreview 显示 skipped |
| `sandbox_created` | 内部 | 忽略 |
| `sandbox_connected` | 内部 | 忽略 |
| `sandbox_paused` | 内部 | 忽略 |
| `sandbox_destroyed` | 内部 | 忽略 |
| `skill_called` | 内部 | 忽略（tool_call_start 已覆盖） |
| `skill_result` | 内部 | 忽略（tool_call_end 已覆盖） |
| `bid_received` | 内部 | 忽略 |
| `agent_assigned` | 内部 | 忽略 |
| `heartbeat` | 内部 | 忽略 |

### 3.3 新增事件（后端需补充）

当前 `engine.py` 的 thinking 过程通过 `llm_response` 事件一起推送，没有明确的 thinking 边界事件。需要新增三个事件：

**`thinking_start`**
```json
{
  "event": "thinking_start",
  "data": {}
}
```

**`thinking_delta`**
```json
{
  "event": "thinking_delta", 
  "data": { "delta": "这道题需要先分析..." }
}
```

**`thinking_end`**
```json
{
  "event": "thinking_end",
  "data": { "duration_ms": 1240 }
}
```

**说明**：现在后端通过 `<thinking>...</thinking>` 标签在 `llm_response` 里混合推送，前端用 `parseThinking()` 解析。改成独立事件后：
- `thinking_delta` 推送思考片段
- `llm_response` 只推送最终回答文字
- 前端无需 `parseThinking()`，逻辑更清晰

> **实现决策**：`thinking_start/delta/end` 的发射点在 `llm/provider.py` 的流式输出处理里，检测到 `<thinking>` tag 时切换推送目标。

---

## 四、前端消息数据结构变更

### 4.1 当前 ChatMessage 结构

```typescript
interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
  streaming?: boolean
  tool_calls?: ToolCall[]
}
```

### 4.2 新增字段

```typescript
interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
  streaming?: boolean

  // 执行过程节点列表（有序，按事件到达顺序插入）
  execution_steps?: ExecutionStep[]
}

// 执行步骤：思考 / 工具调用 / 代码执行 均用此结构
type ExecutionStep =
  | ThinkingStep
  | ToolCallStep
  | CodeExecutionStep

interface ThinkingStep {
  type: 'thinking'
  content: string          // 累积的思考文字
  streaming: boolean       // 是否仍在流式输出
  duration_ms?: number     // 结束后填入
}

interface ToolCallStep {
  type: 'tool_call'
  tool_name: string
  arguments: Record<string, unknown>
  status: 'running' | 'completed' | 'failed'
  result?: Record<string, unknown>
  duration_ms?: number
  started_at: number       // Date.now()
}

interface CodeExecutionStep {
  type: 'code_execution'   // code_executor 工具的专属展示
  code: string             // 执行的代码
  status: 'running' | 'completed' | 'failed' | 'timeout'
  stdout?: string
  stderr?: string
  exit_code?: number
  duration_ms?: number
  started_at: number
}
```

**变更说明**：

- 原 `tool_calls` 字段废弃，迁移到 `execution_steps`
- `code_executor` 工具调用从通用 `ToolCallStep` 中分离为独立的 `CodeExecutionStep`，专门渲染代码和输出
- `execution_steps` 是有序数组，保留事件发生的时序（thinking → tool_call → thinking → tool_call 的穿插顺序）

---

## 五、UI 组件设计

### 5.1 整体气泡结构

```
┌─ AssistantMessage ─────────────────────────────────────────┐
│ [AI头像]  CodeSoul                                          │
│ ┌─ bubble ──────────────────────────────────────────────┐  │
│ │                                                       │  │
│ │  [ThinkingBlock]      ← 思考过程折叠块（可选）         │  │
│ │  [ExecutionStepList]  ← 执行步骤列表（可选）           │  │
│ │  [MarkdownBody]       ← 最终文字回答                   │  │
│ │  [StreamCursor]       ← 流式光标（streaming 时）       │  │
│ │                                                       │  │
│ └───────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

### 5.2 ThinkingBlock 组件

状态变化：

```
[streaming=true]          [streaming=false]
┌──────────────────┐      ┌──────────────────┐
│ ◌ 思考中…  [展开] │  →   │ ✓ 思考过程  [展开] │
│ ─────────────── │      │ ─────────────── │
│ 这道题需要先分析  │      │ （默认折叠）       │
│ 用户的需求...    │      └──────────────────┘
└──────────────────┘
```

- streaming 时：紫色 spinner + "思考中…" + 自动展开
- 结束后：✓ 图标 + "思考过程" + 自动折叠
- 耗时展示在 header 右侧（`1.2s`）

### 5.3 ExecutionStepList 组件

步骤列表作为一个整体折叠块，内部按顺序排列各步骤：

```
┌─ 执行过程 (3步)  ▼ ────────────────────────────┐
│                                               │
│  ① [ToolCallCard: get_weather]  ✓  0.8s      │
│                                               │
│  ② [CodeExecutionCard]          ✓  0.3s      │
│                                               │
│  ③ [ToolCallCard: web_search]   ✓  1.1s      │
│                                               │
└───────────────────────────────────────────────┘
```

- 流式执行时自动展开
- 全部完成后自动折叠（收起状态显示步骤总数）

### 5.4 ToolCallCard 组件

通用工具调用卡片（非代码执行工具）：

```
┌─ ToolCallCard ─────────────────────────────────┐
│ 🔧 web_search              ● 执行中            │  ← running
│ ─────────────────────────────────────────────  │
│ 查询: "Vue 3 最新版本"                           │
└────────────────────────────────────────────────┘

┌─ ToolCallCard ─────────────────────────────────┐
│ 🔧 get_weather             ✓ 成功  0.8s        │  ← completed
│ ─────────────────────────────────────────────  │
│ 查询: 北京                                       │
│ ─────────────────────────────────────────────  │
│ 返回: 晴天 26°C，东南风 3级                       │  ← 人类可读摘要
└────────────────────────────────────────────────┘

┌─ ToolCallCard ─────────────────────────────────┐
│ 🔧 http_request            ✗ 失败  0.4s        │  ← failed
│ ─────────────────────────────────────────────  │
│ 查询: GET https://api.example.com/data          │
│ ─────────────────────────────────────────────  │
│ 错误: Connection timeout                         │
└────────────────────────────────────────────────┘
```

**结果摘要渲染规则**（针对不同工具定制展示，而非裸 JSON）：

| 工具 | 摘要字段提取规则 |
|------|----------------|
| `get_weather` | `{city} {current.description} {current.temperature}{unit}` |
| `web_search` | `找到 {results.length} 条结果` |
| `http_request` | `{status_code} {url}` |
| `update_profile` | `昵称已更新为 {nickname}` |
| 其他 | `success: {result.success}` 或截断 JSON |

### 5.5 CodeExecutionCard 组件（重点）

`code_executor` 工具专属卡片：

**执行中状态**：

```
┌─ CodeExecutionCard ────────────────────────────┐
│ ⚡ 执行代码                ● 运行中             │
│ ─────────────────────────────────────────────  │
│ ┌─ Python ──────────────────────────────────┐  │
│ │ def fibonacci(n):                          │  │
│ │     if n <= 1: return n                    │  │
│ │     return fibonacci(n-1) + fibonacci(n-2) │  │
│ │ print([fibonacci(i) for i in range(10)])   │  │
│ └────────────────────────────────────────────┘  │
│ [■■■■■□□□□□] 执行中...                          │  ← 进度动画
└────────────────────────────────────────────────┘
```

**成功状态**：

```
┌─ CodeExecutionCard ────────────────────────────┐
│ ⚡ 执行代码                ✓ 成功  0.3s         │
│ ─────────────────────────────────────────────  │
│ ┌─ Python ──────────────────────────────────┐  │
│ │ def fibonacci(n): ...                      │  │  ← 代码（可折叠）
│ └────────────────────────────────────────────┘  │
│ ─────────────────────────────────────────────  │
│ 输出                                            │
│ ┌───────────────────────────────────────────┐  │
│ │ [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]         │  │
│ └───────────────────────────────────────────┘  │
└────────────────────────────────────────────────┘
```

**失败状态**：

```
┌─ CodeExecutionCard ────────────────────────────┐
│ ⚡ 执行代码                ✗ 失败  0.2s         │
│ ─────────────────────────────────────────────  │
│ ┌─ Python ──────────────────────────────────┐  │
│ │ import pandas as pd ...                    │  │
│ └────────────────────────────────────────────┘  │
│ ─────────────────────────────────────────────  │
│ 错误输出                                         │
│ ┌───────────────────────────────────────────┐  │
│ │ ModuleNotFoundError:                       │  │
│ │   No module named 'pandas'                 │  │
│ └────────────────────────────────────────────┘  │
└────────────────────────────────────────────────┘
```

**超时状态**：

```
┌─ CodeExecutionCard ────────────────────────────┐
│ ⚡ 执行代码                ⏱ 超时  30s          │
│ ─────────────────────────────────────────────  │
│ 执行超时（30秒），代码已停止                        │
└────────────────────────────────────────────────┘
```

### 5.6 整体进度指示器

在气泡顶部（非 header，在 bubble 内）增加一个轻量全局进度条，仅在 `streaming=true` 时显示：

```
┌─ bubble ─────────────────────────────────────┐
│ ▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 执行中   │  ← 进度条
│                                              │
│ [ThinkingBlock]                              │
│ ...                                          │
└──────────────────────────────────────────────┘
```

- 使用 indeterminate 样式（无限循环），不伪装成精确进度
- 完成后渐隐消失

---

## 六、后端变更

### 6.1 新增 SSE 事件类型

在 `sse.py` 的 `SSEEventTypes` 中新增：

```python
THINKING_START = "thinking_start"
THINKING_DELTA = "thinking_delta"
THINKING_END   = "thinking_end"
SANDBOX_EXECUTING = "sandbox_executing"   # 替代 SANDBOX_CODE_EXECUTING，语义更简洁
PIPELINE_STARTED = "pipeline_started"
STAGE_STARTED    = "stage_started"
STAGE_COMPLETED  = "stage_completed"
STAGE_SKIPPED    = "stage_skipped"
```

新增对应的 emit 函数：
```python
async def emit_thinking_start(task_id: str) -> None: ...
async def emit_thinking_delta(task_id: str, delta: str) -> None: ...
async def emit_thinking_end(task_id: str, duration_ms: int) -> None: ...
async def emit_sandbox_executing(task_id: str, code: str) -> None: ...
async def emit_pipeline_started(task_id: str, project_id: str, session_id: str, pipeline_run_id: str, intent_type: str) -> None: ...
async def emit_stage_started(task_id: str, project_id: str, session_id: str, pipeline_run_id: str, stage_id: str) -> None: ...
async def emit_stage_completed(task_id: str, project_id: str, session_id: str, pipeline_run_id: str, stage_id: str) -> None: ...
async def emit_stage_skipped(task_id: str, project_id: str, session_id: str, pipeline_run_id: str, stage_id: str, reason: str) -> None: ...
```

TASK-015 后，StageRuntime 在调用 `SkillExecutionEngine` 前后发射 `pipeline_started`、`stage_started`、`stage_completed`；用户手动跳过可选阶段时后端状态持久化为 `skipped`，前端通过 PipelineRun API 刷新 StagePreview。`stage_skipped` 事件类型已预留给后续异步阶段跳过场景。

### 6.2 LLM Provider 流式输出拆分

在 `llm/provider.py` 的流式处理中，检测 `<thinking>` 标签切换事件类型：

```
流式 chunk → 检测标签边界：
  遇到 <thinking>   → emit thinking_start，后续 chunk → emit thinking_delta
  遇到 </thinking>  → emit thinking_end
  普通文字          → emit llm_response
```

当前逻辑是把全部内容通过 `llm_response` 推送，前端用 `parseThinking()` 分离。  
改造后前端直接消费分离好的事件，`parseThinking()` 可以删除。

### 6.3 code_executor Skill 补充事件

在 `skills/code_executor.py` 的 `code_executor()` 函数执行前后，通过 `on_event` 回调推送：

```python
# 执行前
await on_event("sandbox_executing", {"code": code})

# 执行后（成功）
await on_event("sandbox_completed", {
    "exit_code": result.exit_code,
    "duration_ms": result.duration_ms,
})

# 超时
await on_event("sandbox_timeout", {"timeout_seconds": timeout})
```

**问题**：`code_executor()` 当前签名不接受 `on_event` 回调，需要调整。  
`SkillDispatcher.invoke()` 已有 `on_event` 参数，需要在 `dispatcher.py` 中把 `on_event` 透传给执行函数（仅当函数签名接受时，同现有的 `user_id` 注入机制）。

### 6.4 Dispatcher 注入 on_event

`dispatcher.py` 中已有 `user_id` 的动态注入逻辑，同样方式注入 `on_event`：

```python
sig = inspect.signature(executor)
if "on_event" in sig.parameters:
    call_args["on_event"] = on_event
if "user_id" in sig.parameters:
    call_args["user_id"] = user_id
```

---

## 七、前端变更

### 7.1 useChat.ts — 新增事件处理

```typescript
case 'thinking_start': {
  sessionStore.startThinkingStep(localId)
  break
}
case 'thinking_delta': {
  const delta = event.data.delta as string
  sessionStore.appendThinkingDelta(localId, delta)
  break
}
case 'thinking_end': {
  sessionStore.endThinkingStep(localId, event.data.duration_ms as number)
  break
}
case 'sandbox_executing': {
  sessionStore.startCodeExecution(localId, event.data.code as string)
  break
}
case 'sandbox_completed': {
  // tool_call_end 会带完整结果，这里只更新耗时
  sessionStore.updateCodeExecutionTiming(localId, event.data.duration_ms as number)
  break
}
case 'sandbox_timeout': {
  sessionStore.failCodeExecution(localId, 'timeout')
  break
}
case 'pipeline_started':
case 'stage_started':
case 'stage_completed':
case 'stage_skipped': {
  pipelineStore.fetchRun(event.data.pipeline_run_id as string)
  break
}
```

### 7.2 session store — 新增 execution_steps 操作

```typescript
// 新增 action 列表（替代现有 appendToolCall）
startThinkingStep(msgId: string): void
appendThinkingDelta(msgId: string, delta: string): void
endThinkingStep(msgId: string, durationMs: number): void

startToolCallStep(msgId: string, toolName: string, args: Record<string, unknown>): void
completeToolCallStep(msgId: string, toolName: string, result: Record<string, unknown>, durationMs: number): void
failToolCallStep(msgId: string, toolName: string, error: string): void

startCodeExecution(msgId: string, code: string): void
completeCodeExecution(msgId: string, stdout: string, stderr: string, exitCode: number, durationMs: number): void
failCodeExecution(msgId: string, reason: 'error' | 'timeout'): void
```

### 7.3 新增/改造组件清单

| 组件 | 操作 | 说明 |
|------|------|------|
| `ThinkingBlock.vue` | 改造 | 增加 streaming prop，区分 spinner/✓ 状态 |
| `ExecutionStepList.vue` | 新增 | 包裹所有步骤的折叠容器 |
| `ToolCallCard.vue` | 新增 | 通用工具调用卡片，含摘要渲染 |
| `CodeExecutionCard.vue` | 新增 | code_executor 专属卡片 |
| `ExecutionProgressBar.vue` | 新增 | 气泡顶部 indeterminate 进度条 |
| `AssistantMessage.vue` | 改造 | 引入新组件，废弃原 tool-calls-block 内联代码 |

---

## 八、事件时序示例

以"帮我写一个计算斐波那契数列的函数并执行" 为例：

```
后端推送顺序                        前端 UI 变化
──────────────────────────────────  ──────────────────────────────
task_started                    →   进度条出现，bubble 空白
thinking_start                  →   ThinkingBlock 出现，spinner 转
thinking_delta × N              →   thinking 文字流式出现
thinking_end (1200ms)           →   spinner → ✓，自动折叠，显示 1.2s
sandbox_executing (code=...)    →   CodeExecutionCard 出现，代码内容填入卡片
                                    [代码块 + 进度动画]
sandbox_completed (300ms)       →   进度动画消失，显示耗时
tool_call_end (stdout/stderr)   →   输出区域填入结果，状态→✓ 成功
llm_response × N                →   主文字气泡逐字流式
task_completed                  →   进度条消失，streaming=false
                                    ExecutionStepList 自动折叠
```

---

## 九、不做什么（范围排除）

- **不展示** `sandbox_id`、`host`、`port`、`template_id` 等基础设施字段
- **不展示** `bid_received`、`agent_assigned`（Contract Net 协议内部）
- **不实现** 代码执行的"实时 stdout 流式输出"（当前沙箱接口是等待结束后返回完整输出）
- **不实现** 在 UI 上重新执行代码的功能（超出本任务范围）
- **不改变** SSE 的传输协议和鉴权方式

---

## 十、实施顺序

### Phase 1：后端事件补齐（先行）
1. `sse.py` 新增 `thinking_start/delta/end`、`sandbox_executing` 事件类型和 emit 函数
2. `llm/provider.py` 流式处理中拆分 thinking/response 事件
3. `dispatcher.py` 注入 `on_event` 到 Skill 执行函数
4. `code_executor.py` 接收 `on_event`，在执行前后发射事件

### Phase 2：数据层（Store 和类型）
1. 更新 `types/index.ts` 中 `ChatMessage` 类型
2. 改造 `session.ts` store，新增 `execution_steps` 相关 actions
3. 更新 `useChat.ts` 处理新事件

### Phase 3：UI 组件
1. 新增 `CodeExecutionCard.vue`（优先，最高价值）
2. 新增 `ToolCallCard.vue`（替换现有通用展示）
3. 新增 `ExecutionStepList.vue`
4. 改造 `ThinkingBlock.vue`
5. 新增 `ExecutionProgressBar.vue`
6. 改造 `AssistantMessage.vue` 接入新组件

### Phase 4：联调验证
1. 端到端测试：天气查询（tool_call）、代码执行（sandbox）、思考+执行（穿插）
2. 边界场景：超时、失败、多工具调用、thinking + 多轮工具调用穿插
