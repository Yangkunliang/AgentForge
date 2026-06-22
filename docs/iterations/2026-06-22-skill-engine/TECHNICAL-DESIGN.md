# Skill Engine — 技术设计文档

**迭代版本**：2026-06-22-skill-engine  
**LLM 平台**：阿里云百炼 DeepSeek-V3（通过 LiteLLM `openai/` 前缀接入，完全兼容 OpenAI Function Calling 格式）

---

## 1. 架构概览

```
用户消息
   │
   ▼
sessions.py  ─→  _run_task_with_skills()          ← 新入口（替换原 _run_task_and_update_message）
                       │
                       ├─ 1. 加载 Skill tool 定义（SkillRegistry.get_tools_for_session）
                       │
                       ├─ 2. ReAct Loop（SkillExecutionEngine）
                       │       ┌──────────────────────────────────────┐
                       │       │  LLM.tool_use_complete(messages, tools)│
                       │       │         ↓                             │
                       │       │  has_tool_calls?                      │
                       │       │    YES → SkillDispatcher.invoke()     │
                       │       │              ↓                        │
                       │       │          append tool_result msg       │
                       │       │          SSE: skill_called/result     │
                       │       │         ↓                             │
                       │       │    NO  → 最终回复，退出循环            │
                       │       └──────────────────────────────────────┘
                       │
                       └─ 3. SSE 流式输出最终文本 + task_completed
```

## 2. DeepSeek-V3（百炼）Tool Calling 说明

百炼平台 DeepSeek-V3 完全兼容 OpenAI Function Calling 协议（`/v1/chat/completions`）。  
LiteLLM 调用方式：

```python
# .env 配置
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=sk-xxxx
LLM_MODEL=openai/deepseek-v3   # openai/ 前缀让 LiteLLM 走 OpenAI-compat 路径

# tool_use 调用示例
response = await litellm.acompletion(
    model="openai/deepseek-v3",
    messages=messages,
    tools=tools,           # OpenAI tools 格式
    tool_choice="auto",    # 让模型自行决定是否调用工具
)
# 响应格式与 OpenAI 完全一致
tool_calls = response.choices[0].message.tool_calls
```

**注意**：DeepSeek-V3 不支持流式 + tool_use 同时启用（部分版本限制）。  
当前方案：tool_use 轮次用**非流式**完成，最终文本回复用**流式**输出给用户。

## 3. 新增文件结构

```
src/agent_forge/skills/
├── __init__.py
├── manifest.py          ✅ 已有（解析 skill.md）
├── manager.py           ✅ 已有（CRUD）
├── loader.py            ✅ 已有（本地目录扫描）
├── installer.py         ✅ 已有（GitHub/PyPI 安装）
├── builtin.py           ✅ 已有（注册内置 Skill）
├── web_search.py        ✅ 已有（DuckDuckGo）
├── weather.py           🆕 内置天气 Skill（Open-Meteo）
├── registry.py          🆕 运行时 Skill 注册表（tool 定义缓存）
├── dispatcher.py        🆕 Skill 调度器（根据 tool_name 路由到执行函数）
└── engine.py            🆕 ReAct 执行引擎（tool_use 循环）

src/api/routes/
└── skills.py            ✅ 已有，补充 marketplace GitHub Topic 查询
```

## 4. 数据模型变更

### 4.1 `skills` 表新增字段

```sql
ALTER TABLE skills ADD COLUMN enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE skills ADD COLUMN source_type VARCHAR(20) DEFAULT 'builtin';
-- source_type: builtin | local | github | pypi | clawhub
ALTER TABLE skills ADD COLUMN icon_url VARCHAR(500);
ALTER TABLE skills ADD COLUMN tags JSON DEFAULT '[]';
ALTER TABLE skills ADD COLUMN github_url VARCHAR(500);
```

### 4.2 `agent_skills` 表新增字段

```sql
ALTER TABLE agent_skills ADD COLUMN enabled BOOLEAN NOT NULL DEFAULT TRUE;
```

对应 migration：`migrations/alembic/versions/002_skill_engine.py`

## 5. SkillRegistry（registry.py）

负责在运行时缓存 Skill 的 tool 定义，避免每次请求都查 DB。

```python
class SkillRegistry:
    """运行时 Skill 注册表，缓存 tool 定义"""

    _instance: SkillRegistry | None = None
    _tool_cache: dict[str, list[dict]]    # skill_name → [OpenAI tool def]
    _executor_cache: dict[str, Callable]  # tool_function_name → executor func

    async def get_all_tools(db: AsyncSession) -> list[dict]:
        """获取所有启用 Skill 的 tool 定义列表（用于注入 LLM）"""

    async def get_tools_for_agent(db, agent_id: str) -> list[dict]:
        """获取指定 Agent 绑定且启用的 Skill 的 tool 定义"""

    def get_executor(tool_name: str) -> Callable | None:
        """根据 tool function name 获取对应执行函数"""

    def register_executor(tool_name: str, func: Callable) -> None:
        """注册内置 Skill 的执行函数"""

    def invalidate(skill_name: str) -> None:
        """安装/卸载后清除缓存"""
```

## 6. SkillDispatcher（dispatcher.py）

```python
class SkillDispatcher:
    """根据 LLM 返回的 tool_call 路由到对应执行函数"""

    async def invoke(
        self,
        tool_name: str,
        tool_call_id: str,
        arguments: dict,
        on_event: Callable[[str, dict], Awaitable[None]] | None = None,
    ) -> str:
        """
        执行一次 tool_call。

        1. 从 SkillRegistry 取执行函数
        2. asyncio.wait_for(func(**arguments), timeout=30)
        3. 把结果序列化为 JSON string（LLM tool role message 要求）
        4. 通过 on_event 回调推送 SSE skill_called / skill_result 事件
        5. 返回结果字符串
        """
```

## 7. SkillExecutionEngine（engine.py）

ReAct 循环核心，替换原 `_run_task_and_update_message` 的 LLM 调用部分。

```python
class SkillExecutionEngine:
    MAX_ROUNDS = 5  # 防止无限循环

    async def run(
        self,
        user_message: str,
        tools: list[dict],
        llm: LiteLLMProvider,
        config: LLMConfig,
        sse_publish: Callable[[str, dict], Awaitable[None]],
    ) -> str:
        """
        ReAct 循环：
        1. 构造 messages（system + history + user）
        2. 调用 LLM（带 tools）
        3. 如果有 tool_calls → 执行 → 追加 tool result → 继续
        4. 没有 tool_calls → 返回最终文本
        5. 最终文本通过 stream_complete 流式推给 SSE
        """
```

**消息格式**（OpenAI / DeepSeek-V3 兼容）：

```python
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user",   "content": "明天北京天气怎么样？"},
    # LLM 第一轮返回 tool_call
    {"role": "assistant", "content": None,
     "tool_calls": [{"id": "call_abc", "type": "function",
                     "function": {"name": "get_weather",
                                  "arguments": '{"city":"北京"}'}}]},
    # Skill 执行结果追加为 tool role
    {"role": "tool", "content": '{"temp":26,"desc":"晴","humidity":40,...}',
     "tool_call_id": "call_abc"},
    # LLM 第二轮根据 tool 结果生成最终回复（无 tool_calls → 退出循环）
]
```

## 8. 内置天气 Skill（weather.py）

```python
# Tool 定义（注入 LLM）
GET_WEATHER_TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "查询指定城市的实时天气和未来预报。当用户询问天气相关问题时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名称，如 '北京'、'上海'、'London'"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"],
                         "description": "温度单位，默认 celsius"},
            },
            "required": ["city"],
        },
    },
}

async def get_weather(city: str, unit: str = "celsius") -> dict:
    """
    1. Open-Meteo Geocoding API 将城市名转换为经纬度
    2. Open-Meteo Weather API 获取天气数据
    3. 返回结构化天气字典
    """
```

## 9. sessions.py 修改

将 `_run_task_and_update_message` 替换为 `_run_task_with_skills`：

```python
async def _run_task_with_skills(task_id, assistant_msg_id, description, user_id):
    # 1. 加载 tools（从 DB 获取 user 默认 Agent 的 Skill 列表）
    tools = await SkillRegistry.get_all_tools(db)

    # 2. 如果有 tools，走 ReAct 引擎；否则退化为纯文本生成
    engine = SkillExecutionEngine(dispatcher)
    full_content = await engine.run(description, tools, llm, config, sse.publish)

    # 3. 更新 DB + 推送 task_completed
```

## 10. Skill 市场 API 补充

```
GET /api/v1/skills/marketplace?source=clawhub|github|all
GET /api/v1/skills/marketplace/search?q=天气&source=github
POST /api/v1/skills/{skill_name}/enable
POST /api/v1/skills/{skill_name}/disable
```

GitHub Topic 查询：`https://api.github.com/search/repositories?q=topic:agentforge-skill`

## 11. Migration 002

新增字段通过 `migrations/alembic/versions/002_skill_engine.py` 完成，
包含 `skills.enabled`、`skills.source_type`、`skills.tags`、
`skills.icon_url`、`skills.github_url`、`agent_skills.enabled`。

## 12. SSE 事件扩展

| event | data | 说明 |
|-------|------|------|
| `skill_called` | `{skill: str, tool: str, args: dict}` | Skill 开始执行 |
| `skill_result` | `{skill: str, tool: str, result: str, elapsed_ms: int}` | Skill 执行完毕 |

前端 `useSSE.ts` 已有 `skill_called` / `skill_result` 类型定义，无需修改。  
`SessionSidebar` 和 chat 消息气泡默认不展示这两个内部事件（保持多 Agent 复杂度对用户透明的原则）。
