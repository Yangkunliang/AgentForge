# LLM 配置与设计 (LLM-CONFIG.md)

## 1. 架构设计

### 1.1 模块位置

LLM 相关代码集中在 `src/agent_forge/llm/`：

```
src/agent_forge/llm/
├── __init__.py          # 统一导出：Provider / Config / Response / Fallback / ModelRouter
├── provider.py          # 核心实现：接口 + LiteLLM + Fallback + Tracing
└── router.py            # Provider / Model / Credential / Route 解析
```

Skill 执行引擎在 `src/agent_forge/skills/engine.py`，负责 LLM ↔ Skill 的多轮 `tool_use` 循环。
结构化配置模型在 `src/agent_forge/models/llm.py`，API 在 `src/api/routes/llm.py`。

### 1.2 Provider 接口

```python
class LLMProvider(ABC):
    """所有 LLM 调用的统一抽象"""

    async def complete(self, prompt: str, config: LLMConfig | None = None) -> LLMResponse: ...
    """单轮非流式：system prompt + user prompt → 完整回复"""

    async def stream_complete(
        self,
        prompt: str,
        config: LLMConfig | None = None,
        on_thinking_start: Callable[[], Awaitable[None]] | None = None,
        on_thinking_delta: Callable[[str], Awaitable[None]] | None = None,
        on_thinking_end: Callable[[int], Awaitable[None]] | None = None,
        system_prompt: str | None = None,
    ) -> AsyncGenerator[str, None]: ...
    """流式：拆分 thinking / 正文，通过回调推送 thinking 事件"""

    async def chat_complete(self, messages: list[dict], config: LLMConfig | None = None) -> LLMResponse: ...
    """多轮对话：传入完整 messages 列表（含 history）"""

    async def tool_use_complete(
        self,
        messages: list[dict],
        tools: list[dict],
        config: LLMConfig | None = None,
    ) -> LLMResponse: ...
    """工具调用决策（非流式）：LLM 返回 tool_calls → SkillDispatcher 执行"""

    async def tool_use_stream(
        self,
        messages: list[dict],
        tools: list[dict],
        config: LLMConfig | None = None,
    ) -> AsyncGenerator[str | ToolCall, None]: ...
    """工具调用决策（流式）：边生成边解析 reasoning + tool_calls"""
```

### 1.3 统一调用流程

```
SkillExecutionEngine (ReAct 循环)
    │
    ▼
ModelRouter.resolve_model_route (阶段模型路由)
    │
    ▼
LLMProvider.tool_use_complete (工具路由决策)
    │
    ├─ has_tool_calls=True  → SkillDispatcher.invoke → 追加 tool result → 下一轮
    │
    └─ has_tool_calls=False → LLMProvider.stream_complete → 流式最终回复
                                      │
                                      ├─ on_thinking_start / delta / end (思考过程)
                                      └─ yield (正文 chunk)
```

### 1.4 全局单例

```python
# provider.py 底部
def get_llm_provider() -> LLMProvider:
    """返回 LiteLLMProvider（可用）或 FallbackLLMProvider（降级）"""
```

应用启动时无需手动初始化，首次调用 `get_llm_provider()` 自动创建。

---

## 2. 配置管理

### 2.1 legacy 配置文件位置

旧版全局配置仍集中在 `src/agent_forge/config.py`（Pydantic `BaseSettings`），从 `.env` 和环境变量加载，并作为 ModelRouter 的 legacy fallback：

```python
# LLM
llm_base_url: str          # LLM_BASE_URL — 代理或兼容 API 的 base URL
api_key: str               # LLM_API_KEY  — 统一 API Key
default_model: str         # LLM_MODEL    — 默认模型（如 "openai/gpt-4o-mini"）
default_temperature: float # 默认温度
max_tokens: int            # 默认最大 token 数

# 多模型路由
vision_model: str          # VL_MODEL — 图像理解专用
image_gen_model: str       # T2I_MODEL — 文生图专用
model_routes: str          # MODEL_ROUTES — JSON: {"claude": "anthropic/claude-3-5-sonnet"}

# Embedding
embedding_model: str       # EMBEDDING_MODEL
embedding_dimension: int   # EMBEDDING_DIM
```

### 2.2 结构化 ModelRoute

TASK-030 后，后台 LLM 设置页和 `/api/v1/llm/*` 维护四类用户级对象：

| 对象 | 表 | 作用 |
|------|----|------|
| Provider | `llm_providers` | 供应商和 base_url |
| Model | `llm_models` | 模型名、能力、上下文窗口和价格元数据 |
| Credential | `llm_credentials` | 加密保存 API Key，API 只返回 masked 信息 |
| Route | `llm_routes` | 阶段/Agent 引用的 route_key、模型、密钥、超时和 fallback |

StageRuntime 会用以下优先级解析模型：

1. 本次请求上下文中的 `model_route_key`
2. AgentProfile 的 `default_model_route_key`
3. StageDefinition 的 `model_route_key`
4. legacy settings fallback

`config.Settings.model_routes_map` 属性自动合并用户自定义路由 + 多模态模型：

```python
settings.model_routes_map
# 示例返回: {"claude": "anthropic/claude-3-5-sonnet", "vision": "openai/gpt-4o", "image_gen": "dall-e-3"}
```

**不使用的 YAML 文件方式**。新路由优先存数据库；环境变量 JSON 只作为兼容兜底。

### 2.3 环境变量速查

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `LLM_BASE_URL` | (空) | 代理 URL 或兼容 API 地址 |
| `LLM_API_KEY` | (空) | 统一 API Key |
| `LLM_MODEL` | `openai/gpt-4o-mini` | 默认模型 |
| `VL_MODEL` | (空) | 视觉模型 |
| `T2I_MODEL` | (空) | 文生图模型 |
| `MODEL_ROUTES` | `{}` | 多模型路由 JSON |
| `EMBEDDING_MODEL` | `openai/text-embedding-3-small` | Embedding 模型 |

### 2.4 Credential 安全

- 创建 Credential 时只接收一次明文 `secret`。
- 服务端使用 `agent_forge.security.credentials.encrypt_secret()` 加密存储。
- API 响应只返回 `secret_set` 和 `masked_secret`。
- SkillExecutionEngine 的 prompt 上下文只包含 route、provider、model 和 credential 名称，不包含明文 secret。

---

## 3. Prompt 管理

### 3.1 两级 Prompt 体系

项目使用 **两级 Prompt**：

| 层级 | 位置 | 用途 |
|------|------|------|
| **全局 System Prompt** | `provider.py::DEFAULT_SYSTEM_PROMPT` | 每次 `complete()` / `chat_complete()` 自动注入，约束 thinking 格式与行为准则 |
| **Agent System Prompt** | `engine.py::SYSTEM_PROMPT` | Skill 执行引擎在 ReAct 循环中注入，定义 Agent 身份与工具使用规则 |

### 3.2 全局 System Prompt（provider.py）

每次 LLM 调用自动注入，不随需求变化：

```python
DEFAULT_SYSTEM_PROMPT = (
    "你是一个多智能体协同框架的 AI 助手。请遵循以下回答规范：\n"
    "\n"
    "## 思考过程\n"
    "- 如需推理分析，请在 <thinking>...</thinking> 标签内完成。\n"
    "- 思考过程请使用平铺直叙的段落文字，不要使用 markdown 标题。\n"
    "\n"
    "## 正文回复\n"
    "- 在 <thinking> 标签之外输出面向用户的正式回复。\n"
    "- 可以使用完整的 markdown 格式。\n"
)
```

### 3.3 Agent System Prompt（engine.py）

Skill 执行引擎在 ReAct 循环开始时注入，每次会话可注入不同 `agent_name`：

```python
SYSTEM_PROMPT = """你是 {agent_name}，一个面向全栈开发工程师的 AI 智能助手。

**身份**：
- 你唯一的名字是 {agent_name}。
- 不要透露底层模型、平台或框架的名称。

**工具使用规则**：
1. 需要实时数据时，必须调用相应工具，严禁凭记忆猜测。
2. 需要执行代码时，必须调用沙箱工具。
3. 思考过程写在 <thinking>...</thinking> 标签内。
"""
```

### 3.4 动态 Prompt 构建

**不再使用 YAML 模板文件**。所有 Prompt 直接在 Python 代码中以三引号字符串定义，按需 `format()` 注入变量：

```python
system_prompt = _build_system_prompt(agent_name="CodeSoul")  # engine.py
```

如果需要未来迁移到模板存储，建议保持当前字符串 + `format()` 模式，只需将字符串来源改为 DB / 文件系统读取。

### 3.5 最终回复 Prompt

工具执行完成后，`engine.py::_build_final_prompt()` 从 messages 中提取 tool results，构造汇总 prompt：

```python
f"用户问题：{user_question}\n\n工具返回的真实数据：\n{combined}\n\n"
f"请用自然语言、清晰友好地整理并回答用户的问题..."
```

---

## 4. 流式 Thinking 拆分

### 4.1 双来源 thinking

`_stream_with_thinking()` 从 LiteLLM 流式响应中同时处理两类 thinking 来源：

| 来源 | 字段 | 适用模型 |
|------|------|---------|
| 原生 reasoning | `delta.reasoning` | o1 / Claude (compat) |
| 内嵌标签 | `delta.content` 中的 `<thinking>...</thinking>` | DeepSeek-R1 等 |

### 4.2 处理逻辑

```
流式 chunk 到达
    │
    ├─ delta.reasoning 非空 → on_thinking_delta(reasoning)  ← 不 yield
    │
    └─ delta.content 非空 → 检查 <thinking> 标签边界
                          │
                          ├─ 在 thinking 内 → on_thinking_delta(content)
                          └─ 在 thinking 外 → yield(content)  ← 正文输出
```

### 4.3 跨 chunk 标签保护

如果 `<thinking>` 或 `</thinking>` 被拆到两个 chunk 中，`_suffix_match()` 会检测后缀匹配并 buffer 待合并，不会误触发状态切换。

### 4.4 SSE 推送

SkillExecutionEngine 为 thinking 事件设置了三个回调，全部通过 SSE 推送到前端：

| 事件 | 回调 | SSE 类型 |
|------|------|---------|
| thinking 开始 | `on_thinking_start` | `"thinking_start"` |
| thinking 增量 | `on_thinking_delta(delta)` | `"thinking_delta"` |
| thinking 结束 | `on_thinking_end(duration_ms)` | `"thinking_end"` |

---

## 5. ReAct 多轮 tool_use 循环

### 5.1 执行引擎

`SkillExecutionEngine` 在 `src/agent_forge/skills/engine.py` 中实现，核心循环：

```python
for round_num in range(1, MAX_ROUNDS + 1):  # MAX_ROUNDS = 5
    if messages[-1].role == "tool":
        # 有工具结果 → 直接 stream_complete 生成最终回复
        yield from _stream_final(...)
    else:
        response = llm.tool_use_complete(messages, tools, config)
        if response.has_tool_calls:
            # 执行工具 → 追加 tool result → 下一轮
            await dispatcher.invoke(...)
        else:
            # 无工具调用 → 直接流式回复
            yield from _stream_final(user_message)
```

### 5.2 关键优化：省掉多余 LLM 调用

**旧流程**（3 次 LLM 调用）：
```
round 1: tool_use_complete → has_tool_calls=true  → 执行工具
round 2: tool_use_complete → has_tool_calls=false → content 被丢弃（浪费）
round 3: stream_complete   → 重新生成相同内容     ← 多余，浪费 3~5s
```

**新流程**（2 次 LLM 调用）：
```
round 1: tool_use_complete → has_tool_calls=true  → 执行工具
round 2: stream_complete   → 直接流式生成最终回复  ← 省掉一次 LLM 调用
```

判断依据：`messages[-1].role == "tool"` 表示刚执行完工具，直接走 `stream_complete` 生成最终回复。

### 5.3 ToolCall 数据模型

```python
@dataclass
class ToolCall:
    id: str
    function_name: str
    function_args: dict[str, Any]
```

`LLMResponse.tool_calls` 返回 `list[ToolCall]`，`LLMResponse.has_tool_calls` 提供快捷判断。

---

## 6. Fallback 策略

### 6.1 Provider 级降级

`FallbackLLMProvider` 是 `LLMProvider` 的降级实现，在 LiteLLM 不可用或导入失败时启用：

```python
def get_llm_provider() -> LLMProvider:
    p = LiteLLMProvider()
    return p if p.is_available else FallbackLLMProvider()
```

Fallback 返回结构化响应但不实际调用 LLM：
- `complete()` → `[Fallback] {prompt[:80]}`
- `stream_complete()` → 逐字符 yield
- `chat_complete()` → `[Fallback] {last_message}`

### 6.2 单次调用异常

每个方法都有 `try/except`，记录错误日志后重新抛出异常。调用方（SkillExecutionEngine）对 `stream_complete` 捕获了异常并返回友好提示。

### 6.3 模型级降级

**未实现**。当前所有调用都使用 `config.model` 指定的模型，没有自动降级到其他模型的逻辑。如需实现，可在 `LiteLLMProvider` 的 `except` 块中尝试备选模型。

---

## 7. Cost 追踪

### 7.1 调用级追踪

每次 LLM 调用返回的 `LLMResponse` 包含：

```python
@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int      # response.usage.total_tokens
    cost_usd: float       # response.usage.cost
    latency_ms: int
    _tool_calls: list[ToolCall] | None
```

通过 `_tag_tokens()` 将 token 用量写入当前 tracing span tags。

### 7.2 持久化追踪

TASK-045 后，SkillExecutionEngine 会把非流式 `tool_use_complete` 返回的 token、cost 和 latency 写入 `EvalEvent`：

- `event_type=llm_tool_use_completed`
- `tokens_used` / `cost_usd` / `latency_ms` 来自 `LLMResponse`
- `project_id`、`pipeline_run_id`、`stage_id`、`agent_profile_id`、`model_route_key` 来自 StageRuntime 注入的 `advanced_context`
- `metadata_json` 只记录 call type、轮次、可见工具数量和 tool call 名称，不记录 prompt、messages、源码正文或凭据

历史 Cost API 仍保留 Task / TaskExecution 维度：

- `Task.total_cost_usd` — 任务总成本
- `TaskExecution.model_used` / `TaskExecution.cost_usd` — 子任务级明细

### 7.3 API 端点

```http
GET /api/v1/cost?date=2026-06-28
```

响应：

```json
{
  "date": "2026-06-28",
  "total_cost_usd": 15.50,
  "model_costs": {
    "gpt-4o-mini": 10.20,
    "gpt-4o": 3.30,
    "claude-3-sonnet": 2.00
  },
  "total_tasks": 50,
  "avg_cost_per_task": 0.31
}
```

实现位于 `src/agent_forge/api/routes/cost.py`。

---

## 8. Tracing

### 8.1 自动采集

关键方法使用 `@span("llm.*")` 装饰器自动采集：

| 方法 | Span 名称 | 采集 tags |
|------|-----------|-----------|
| `complete()` | `llm.complete` | model, tokens |
| `chat_complete()` | `llm.chat_complete` | model, tokens |
| `tool_use_complete()` | `llm.tool_use_complete` | model, tools(数量), msgs(数量), has_tool_calls, tool_names |
| `stream_complete()` | `llm.stream_complete` | model, prompt_len, chunks, ttfc_ms |
| `tool_use_stream()` | `llm.tool_use_stream` | model, tokens |

### 8.2 Thinking 延迟指标

`ttfc_ms` (time-to-first-chunk) 在 `stream_complete()` 中自动记录，是衡量用户感知延迟的关键指标。

---

## 9. 性能优化与后续增强

结构化 ModelRoute 已经落地；以下是后续优化方向，不属于当前运行时必需契约：

| 功能 | 状态 | 备注 |
|------|------|------|
| 相同任务响应缓存 (TTL 1h) | 后续增强 | 可基于 Redis + prompt hash |
| Prompt 模板缓存 | 后续增强 | 当前 Prompt 硬编码在 Python 中 |
| 模型选择结果缓存 | 后续增强 | 可缓存 ModelRouter 解析结果，但必须尊重 Credential 变更 |
| 每模型并发数限制 | 后续增强 | 不再采用旧 YAML 方案，建议纳入 Route policy |
| 队列管理 | 后续增强 | 可与 RabbitMQ / PipelineRun 调度结合 |
| stream_complete token / cost 明细进入 EvalEvent | 后续增强 | tool_use_complete 已进入 EvalEvent；流式 usage 待 provider 返回稳定后接入 |

---

## 10. 相关文件索引

| 路径 | 内容 |
|------|------|
| `src/agent_forge/llm/provider.py` | Provider 接口 + LiteLLM + Fallback + Thinking 拆分 + Tracing |
| `src/agent_forge/llm/router.py` | ModelRoute 解析、fallback 和 legacy settings 兜底 |
| `src/agent_forge/llm/__init__.py` | 统一导出 |
| `src/agent_forge/models/llm.py` | LLM Provider / Model / Credential / Route 数据模型 |
| `src/api/routes/llm.py` | LLM 设置 API，含 Credential 脱敏响应 |
| `src/agent_forge/config.py` | LLM 配置（Settings + CubeSandboxConfig） |
| `src/agent_forge/skills/engine.py` | ReAct 执行引擎 + Prompt 定义 + tool_use 循环 |
| `src/agent_forge/api/routes/cost.py` | Cost 统计 API |
| `src/agent_forge/models/task.py` | Task 成本字段 |
| `src/agent_forge/models/task_execution.py` | TaskExecution 成本字段 |
| `docs/tech-design/ARCHITECTURE.md` §3.8 | LLM Provider 抽象层架构概览 |
