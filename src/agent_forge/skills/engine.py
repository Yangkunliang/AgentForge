"""SkillExecutionEngine — ReAct 执行引擎

实现 LLM ↔ Skill 的多轮 tool_use 循环：

  1. 构造 messages（system + history + user）
  2. 调用 LLM（带 tools 定义，非流式）
  3. LLM 返回 tool_calls → SkillDispatcher 执行 → 追加 tool result → 继续
  4. LLM 不再调用工具 → 退出循环，流式输出最终文本
  5. 最终文本逐 chunk yield 给调用方用于 SSE 流式推送

循环上限：MAX_ROUNDS（默认 5），防止无限循环。

DeepSeek-V3（百炼）注意事项：
  - 完全兼容 OpenAI Function Calling 格式
  - tool_use 阶段使用非流式（stream=False）
  - 最终文本回复使用流式（stream=True）
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_forge.llm.provider import LLMConfig, LiteLLMProvider
    from agent_forge.skills.dispatcher import SkillDispatcher

logger = logging.getLogger(__name__)

MAX_ROUNDS = 5

SYSTEM_PROMPT_WITH_TOOLS = """你是 AgentForge 智能助手。你拥有以下工具：
- get_weather: 查询实时天气
- web_search: 搜索互联网获取最新信息
- http_request: 发起 HTTP 请求，调用任意 REST API
- update_profile: 更新用户个人资料（昵称、头像）

**重要规则**：
1. 当用户询问天气、气温、是否下雨时，必须调用 get_weather 工具，严禁凭记忆猜测。
2. 当用户需要最新信息或事实核查时，必须调用 web_search，严禁捏造内容。
3. 当用户需要调用特定 API（如汇率、翻译、查询服务状态等）时，使用 http_request 工具。
4. 当用户请求修改个人信息（如设置昵称、更换头像）时，调用 update_profile 工具。
5. 工具返回结果后，用自然、清晰的语言整理展示给用户，可以使用 markdown 格式。
6. 思考过程写在 <thinking>...</thinking> 标签内，使用平铺文字，不用 markdown 标题。
"""


class SkillExecutionEngine:
    """ReAct 多轮 tool_use 执行引擎"""

    def __init__(self, dispatcher: "SkillDispatcher") -> None:
        self._dispatcher = dispatcher

    async def run(
        self,
        user_message: str,
        conversation_history: list[dict],
        tools: list[dict],
        llm: "LiteLLMProvider",
        config: "LLMConfig",
        sse_publish: Callable[[str, dict], Awaitable[None]],
        user_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        执行 ReAct 循环，返回 async generator，调用方 async for chunk in engine.run(...) 消费。

        注意：此方法本身是 async def 但返回 generator object（非 async generator 语法），
        通过内部 _react_loop 实现，避免 Python async generator 不能 return value 的限制。
        """
        return self._react_loop(
            user_message, conversation_history, tools, llm, config, sse_publish, user_id
        )

    async def _react_loop(
        self,
        user_message: str,
        conversation_history: list[dict],
        tools: list[dict],
        llm: "LiteLLMProvider",
        config: "LLMConfig",
        sse_publish: Callable[[str, dict], Awaitable[None]],
        user_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """真正的 async generator，实现 ReAct 循环逻辑"""

        messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT_WITH_TOOLS},
            *conversation_history,
            {"role": "user", "content": user_message},
        ]

        for round_num in range(1, MAX_ROUNDS + 1):
            logger.info(
                "SkillEngine: round %d/%d, messages=%d, tools=%d",
                round_num, MAX_ROUNDS, len(messages), len(tools),
            )

            if tools:
                response = await llm.tool_use_complete(messages, tools, config)
            else:
                response = await llm.chat_complete(messages, config)

            if response.has_tool_calls:
                # 追加 assistant tool_call 消息
                assistant_msg: dict = {
                    "role": "assistant",
                    "content": response.content or None,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function_name,
                                "arguments": json.dumps(tc.function_args, ensure_ascii=False),
                            },
                        }
                        for tc in response.tool_calls
                    ],
                }
                messages.append(assistant_msg)

                # 执行每个工具
                for tc in response.tool_calls:
                    logger.info(
                        "SkillEngine: calling '%s' args=%s", tc.function_name, tc.function_args
                    )
                    
                    # 发送工具调用开始事件（用于前端展示思考过程）
                    if sse_publish:
                        await sse_publish("tool_call_start", {
                            "tool_name": tc.function_name,
                            "arguments": tc.function_args,
                            "tool_call_id": tc.id,
                        })
                    
                    result_str = await self._dispatcher.invoke(
                        tool_name=tc.function_name,
                        tool_call_id=tc.id,
                        arguments=tc.function_args,
                        on_event=sse_publish,
                        user_id=user_id,
                    )
                    
                    # 发送工具调用完成事件（用于前端展示结果）
                    if sse_publish:
                        try:
                            result_data = json.loads(result_str)
                        except json.JSONDecodeError:
                            result_data = {"result": result_str}
                        await sse_publish("tool_call_end", {
                            "tool_name": tc.function_name,
                            "arguments": tc.function_args,
                            "tool_call_id": tc.id,
                            "result": result_data,
                        })
                    
                    messages.append({
                        "role": "tool",
                        "content": result_str,
                        "tool_call_id": tc.id,
                    })

                # 继续下一轮
                continue

            else:
                # 无 tool_calls：最终回复，流式输出
                final_text = response.content or ""

                if tools and messages[-1].get("role") == "tool":
                    # 有工具结果，用流式重新生成更自然的回复
                    stream_prompt = _build_final_prompt(messages)
                    try:
                        async for chunk in llm.stream_complete(stream_prompt, config):
                            if chunk:
                                yield chunk
                        return
                    except Exception as e:
                        logger.warning("Stream final response failed, fallback: %s", e)
                        yield final_text or "处理完毕，请查看结果。"
                        return

                if not final_text:
                    final_text = "抱歉，未能生成回复，请重试。"

                yield final_text
                return

        # 超过最大轮次兜底
        logger.warning("SkillEngine: exceeded MAX_ROUNDS=%d", MAX_ROUNDS)
        try:
            messages.append({
                "role": "user",
                "content": "请根据以上工具返回的信息，用中文给用户一个完整的回答。",
            })
            summary_resp = await llm.chat_complete(messages, config)
            yield summary_resp.content or "已达到最大执行轮次，请重新提问。"
        except Exception as e:
            logger.error("SkillEngine fallback summary failed: %s", e)
            yield "已达到最大执行轮次，请重新提问。"


def _build_final_prompt(messages: list[dict]) -> str:
    """从 tool 结果构造流式最终回复的 prompt"""
    tool_results: list[str] = []
    user_question = ""

    for msg in messages:
        if msg.get("role") == "user":
            user_question = msg.get("content", "")
        elif msg.get("role") == "tool":
            tool_results.append(msg.get("content", ""))

    combined = "\n\n".join(tool_results)
    return (
        f"用户问题：{user_question}\n\n"
        f"工具返回的真实数据：\n{combined}\n\n"
        f"请用自然语言、清晰友好地整理并回答用户的问题。"
        f"可以使用 markdown 格式，但不要直接复制粘贴 JSON 原文。"
    )
