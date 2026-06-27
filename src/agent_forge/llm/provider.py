"""LLM Provider 抽象层

为所有 LLM 调用注入统一的 system prompt，约束 thinking 格式与行为准则。
支持 tool_use（function calling）循环，让 LLM 在需要时主动调用技能。

Thinking 事件拆分（TASK-009）
------------------------------
stream_complete() 现在接受可选的 thinking 回调参数：
  on_thinking_start: Callable[[], Awaitable[None]]
  on_thinking_delta: Callable[[str], Awaitable[None]]
  on_thinking_end:   Callable[[int], Awaitable[None]]  # duration_ms

当检测到 <thinking> / </thinking> 标签边界时，自动切换推送目标：
  - thinking 内容 → on_thinking_delta（不走 on_chunk）
  - 正文内容 → yield（调用方消费，同时推送 llm_response）

两类内容严格互斥，同一时刻只推一种事件。
"""

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from litellm import ModelResponse

logger = logging.getLogger("agent_forge.llm")


@dataclass
class ToolCall:
    """LLM 返回的一个工具调用"""

    id: str
    function_name: str
    function_args: dict[str, Any]

    def __repr__(self) -> str:
        return f"ToolCall(id={self.id}, function={self.function_name}({self.function_args!r}))"


# ── 默认 System Prompt ──────────────────────────────────────────

DEFAULT_SYSTEM_PROMPT: str = (
    "你是一个多智能体协同框架的 AI 助手。请遵循以下回答规范：\n"
    "\n"
    "## 思考过程\n"
    "- 如需推理分析，请在 <thinking>...</thinking> 标签内完成。\n"
    "- 思考过程请使用**平铺直叙的段落文字**，不要使用 markdown 标题（### 等）、\n"
    "  任务列表或大写字母标题（如 SUMMARY、KEY LINKS）。\n"
    "- 如需列举要点，请使用 - 短横线列表或 1. 2. 数字列表。\n"
    "\n"
    "## 正文回复\n"
    "- 在 <thinking> 标签之外输出面向用户的正式回复。\n"
    "- 可以使用完整的 markdown 格式（标题、列表、表格等）。\n"
)


def _build_messages(prompt: str, system_prompt: str) -> list[dict]:
    """构造 messages 列表：始终在头部注入 system message。"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]


@dataclass
class LLMConfig:
    """LLM 配置"""

    model: str
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 60


@dataclass
class LLMResponse:
    """LLM 响应"""

    content: str
    model: str
    tokens_used: int
    cost_usd: float
    latency_ms: int
    _tool_calls: list[ToolCall] | None = None

    @property
    def tool_calls(self) -> list[ToolCall]:
        return self._tool_calls or []

    @property
    def has_tool_calls(self) -> bool:
        return bool(self._tool_calls)


class LLMProvider(ABC):
    """LLM Provider 基类"""

    @abstractmethod
    async def complete(self, prompt: str, config: LLMConfig | None = None) -> LLMResponse:
        pass

    @abstractmethod
    async def stream_complete(
        self,
        prompt: str,
        config: LLMConfig | None = None,
        on_thinking_start: Callable[[], Awaitable[None]] | None = None,
        on_thinking_delta: Callable[[str], Awaitable[None]] | None = None,
        on_thinking_end: Callable[[int], Awaitable[None]] | None = None,
    ) -> AsyncGenerator[str, None]:
        """流式完成。
        
        yield 的内容仅为正文（非 thinking）文字 chunk。
        thinking 内容通过回调推送，与 yield 内容严格互斥。
        """
        pass

    @abstractmethod
    async def chat_complete(
        self,
        messages: list[dict],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        pass


class LiteLLMProvider(LLMProvider):
    """LiteLLM Provider（支持多种 LLM）"""

    def __init__(self):
        try:
            import litellm
            from agent_forge.config import settings
            self.litellm = litellm
            self._available = True
            if settings.llm_base_url:
                litellm.api_base = settings.llm_base_url
            if settings.api_key:
                litellm.api_key = settings.api_key
            logger.info("LiteLLM provider initialized")
        except ImportError:
            logger.warning("LiteLLM not installed, using fallback")
            self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    async def complete(self, prompt: str, config: LLMConfig | None = None) -> LLMResponse:
        if not self.is_available:
            return LLMResponse(content="LiteLLM not available", model="none",
                               tokens_used=0, cost_usd=0.0, latency_ms=0)

        config = config or LLMConfig(model="gpt-4o")
        start_time = time.time()
        messages = _build_messages(prompt, DEFAULT_SYSTEM_PROMPT)

        try:
            response = await self.litellm.acompletion(
                model=config.model,
                messages=messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
            latency_ms = int((time.time() - start_time) * 1000)
            return LLMResponse(
                content=response["choices"][0]["message"]["content"],
                model=config.model,
                tokens_used=response.get("usage", {}).get("total_tokens", 0),
                cost_usd=response.get("usage", {}).get("cost", 0.0),
                latency_ms=latency_ms,
            )
        except Exception as e:
            logger.error(f"LiteLLM completion error: {e}")
            raise

    async def stream_complete(
        self,
        prompt: str,
        config: LLMConfig | None = None,
        on_thinking_start: Callable[[], Awaitable[None]] | None = None,
        on_thinking_delta: Callable[[str], Awaitable[None]] | None = None,
        on_thinking_end: Callable[[int], Awaitable[None]] | None = None,
    ) -> AsyncGenerator[str, None]:
        """流式完成，支持 thinking 事件拆分。

        处理两类 thinking 来源：
          1. 模型原生 reasoning 字段（OpenAI o1/o3、部分 Claude）→ delta.reasoning
          2. 模型在 content 中内嵌 <thinking>...</thinking> 标签（DeepSeek-R1 等）

        yield 只输出正文内容；thinking 内容通过回调推送。
        """
        if not self.is_available:
            yield "LiteLLM not available"
            return

        config = config or LLMConfig(model="gpt-4o")
        messages = _build_messages(prompt, DEFAULT_SYSTEM_PROMPT)

        try:
            response = await self.litellm.acompletion(
                model=config.model,
                messages=messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                stream=True,
            )

            async for chunk in _stream_with_thinking(
                response,
                on_thinking_start=on_thinking_start,
                on_thinking_delta=on_thinking_delta,
                on_thinking_end=on_thinking_end,
            ):
                yield chunk

        except Exception as e:
            logger.error(f"LiteLLM stream error: {e}")
            yield f"Error: {e}"

    async def chat_complete(
        self,
        messages: list[dict],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        if not self.is_available:
            return LLMResponse(content="LiteLLM not available", model="none",
                               tokens_used=0, cost_usd=0.0, latency_ms=0)

        config = config or LLMConfig(model="gpt-4o")
        start_time = time.time()

        try:
            response = await self.litellm.acompletion(
                model=config.model,
                messages=messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
            latency_ms = int((time.time() - start_time) * 1000)
            return LLMResponse(
                content=response["choices"][0]["message"]["content"],
                model=config.model,
                tokens_used=response.get("usage", {}).get("total_tokens", 0),
                cost_usd=response.get("usage", {}).get("cost", 0.0),
                latency_ms=latency_ms,
            )
        except Exception as e:
            logger.error(f"LiteLLM chat error: {e}")
            raise

    async def tool_use_complete(
        self,
        messages: list[dict],
        tools: list[dict],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        """工具调用完成（非流式）"""
        if not self.is_available:
            return LLMResponse(content="LiteLLM not available", model="none",
                               tokens_used=0, cost_usd=0.0, latency_ms=0)

        config = config or LLMConfig(model="gpt-4o")
        start_time = time.time()

        try:
            response: Any = await self.litellm.acompletion(
                model=config.model,
                messages=messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                tools=tools,
            )

            latency_ms = int((time.time() - start_time) * 1000)
            choice = response["choices"][0]["message"]
            content: str | None = choice.get("content")
            tool_calls: list[ToolCall] = []

            raw_tool_calls = choice.get("tool_calls") or []
            for tc in raw_tool_calls:
                tool_calls.append(ToolCall(
                    id=tc["id"],
                    function_name=tc["function"]["name"],
                    function_args=json.loads(tc["function"]["arguments"]),
                ))

            return LLMResponse(
                content=content or "",
                model=config.model,
                tokens_used=response.get("usage", {}).get("total_tokens", 0),
                cost_usd=response.get("usage", {}).get("cost", 0.0),
                latency_ms=latency_ms,
                _tool_calls=tool_calls,  # type: ignore[arg-type]
            )
        except Exception as e:
            logger.error(f"LiteLLM tool_use error: {e}")
            raise

    async def tool_use_stream(
        self,
        messages: list[dict],
        tools: list[dict],
        config: LLMConfig | None = None,
    ) -> AsyncGenerator[str | ToolCall, None]:
        """流式工具调用"""
        if not self.is_available:
            yield "LiteLLM not available"
            return

        config = config or LLMConfig(model="gpt-4o")

        try:
            response = await self.litellm.acompletion(
                model=config.model,
                messages=messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                tools=tools,
                stream=True,
            )

            pending_tool_calls: dict[str, ToolCall] = {}

            async for chunk in response:
                delta = chunk["choices"][0].get("delta", {})

                reasoning = delta.get("reasoning") or ""
                if reasoning:
                    yield reasoning

                content = delta.get("content") or ""
                if content:
                    yield content

                raw_tool_calls = delta.get("tool_calls") or []
                for tc in raw_tool_calls:
                    tc_id = tc.get("id", "")
                    if tc_id not in pending_tool_calls:
                        pending_tool_calls[tc_id] = ToolCall(
                            id=tc_id, function_name="", function_args={})

                    pending = pending_tool_calls[tc_id]
                    fn = tc.get("function", {})
                    if fn.get("name"):
                        pending.function_name = fn["name"]
                    if fn.get("arguments"):
                        args_str = fn["arguments"]
                        current_args = json.dumps(pending.function_args)
                        if args_str != current_args:
                            try:
                                pending.function_args = json.loads(
                                    current_args + args_str.lstrip(","))
                            except json.JSONDecodeError:
                                pass

            for tc in pending_tool_calls.values():
                if tc.function_name and tc.function_args:
                    yield tc
        except Exception as e:
            logger.error(f"LiteLLM tool_use stream error: {e}")
            yield f"Error: {e}"


# ── Thinking 流式解析器 ───────────────────────────────────────

async def _stream_with_thinking(
    litellm_response: Any,
    on_thinking_start: Callable[[], Awaitable[None]] | None,
    on_thinking_delta: Callable[[str], Awaitable[None]] | None,
    on_thinking_end: Callable[[int], Awaitable[None]] | None,
) -> AsyncGenerator[str, None]:
    """从 LiteLLM 流式响应中拆分 thinking 和正文内容。

    处理策略：
      - delta.reasoning 非空 → 原生 reasoning 字段（o1/Claude）
      - delta.content 含 <thinking> 标签 → 内嵌标签模式（DeepSeek-R1）
      - 其余 delta.content → 正文，直接 yield

    thinking 内容通过回调推送，yield 只输出正文。
    """
    in_thinking = False
    thinking_start_time: float = 0.0
    # 跨 chunk 的标签缓冲区（处理标签被拆分到两个 chunk 的情况）
    tag_buffer = ""

    OPEN_TAG  = "<thinking>"
    CLOSE_TAG = "</thinking>"

    async def _fire_thinking_start() -> None:
        nonlocal in_thinking, thinking_start_time
        if not in_thinking:
            in_thinking = True
            thinking_start_time = time.time()
            if on_thinking_start:
                await on_thinking_start()

    async def _fire_thinking_end() -> None:
        nonlocal in_thinking, thinking_start_time
        if in_thinking:
            in_thinking = False
            duration_ms = int((time.time() - thinking_start_time) * 1000)
            if on_thinking_end:
                await on_thinking_end(duration_ms)

    async for chunk in litellm_response:
        delta = chunk["choices"][0].get("delta", {})

        # ── 来源 1：原生 reasoning 字段（o1/o3/Claude compat）────
        reasoning = delta.get("reasoning") or ""
        if reasoning:
            await _fire_thinking_start()
            if on_thinking_delta:
                await on_thinking_delta(reasoning)
            continue  # reasoning 和 content 互斥，跳过 content 处理

        # ── 来源 2：content 字段，需解析内嵌 <thinking> 标签 ────
        content = delta.get("content") or ""
        if not content:
            continue

        # 将 tag_buffer 中残留内容和新 chunk 合并处理
        text = tag_buffer + content
        tag_buffer = ""

        while text:
            if in_thinking:
                # 在 thinking 块内，寻找结束标签
                close_idx = text.find(CLOSE_TAG)
                if close_idx == -1:
                    # 检查末尾是否是结束标签的前缀（防止标签被拆断）
                    suffix_len = _suffix_match(text, CLOSE_TAG)
                    if suffix_len:
                        # 末尾可能是不完整的结束标签，放入 buffer 等下一 chunk
                        if on_thinking_delta and text[:-suffix_len]:
                            await on_thinking_delta(text[:-suffix_len])
                        tag_buffer = text[-suffix_len:]
                    else:
                        if on_thinking_delta:
                            await on_thinking_delta(text)
                    break
                else:
                    # 找到结束标签
                    thinking_part = text[:close_idx]
                    if on_thinking_delta and thinking_part:
                        await on_thinking_delta(thinking_part)
                    await _fire_thinking_end()
                    text = text[close_idx + len(CLOSE_TAG):]
                    # 跳过标签后紧跟的换行
                    text = text.lstrip("\n")
            else:
                # 在正文区，寻找开始标签
                open_idx = text.find(OPEN_TAG)
                if open_idx == -1:
                    # 检查末尾是否是开始标签的前缀
                    suffix_len = _suffix_match(text, OPEN_TAG)
                    if suffix_len:
                        body_part = text[:-suffix_len]
                        if body_part:
                            yield body_part
                        tag_buffer = text[-suffix_len:]
                    else:
                        yield text
                    break
                else:
                    # 找到开始标签
                    body_part = text[:open_idx]
                    if body_part:
                        yield body_part
                    await _fire_thinking_start()
                    text = text[open_idx + len(OPEN_TAG):]

    # 流结束时，若仍在 thinking 中（模型未输出结束标签），强制结束
    if in_thinking:
        if tag_buffer and on_thinking_delta:
            await on_thinking_delta(tag_buffer)
        await _fire_thinking_end()
    elif tag_buffer:
        # tag_buffer 中是不完整的开始标签，当作正文输出
        yield tag_buffer


def _suffix_match(text: str, tag: str) -> int:
    """返回 text 末尾与 tag 前缀匹配的最大长度（1 ~ len(tag)-1）。
    
    用于处理标签被拆断到两个 chunk 的情况。
    返回 0 表示无匹配。
    """
    for length in range(min(len(tag) - 1, len(text)), 0, -1):
        if text.endswith(tag[:length]):
            return length
    return 0


# ── Fallback Provider ──────────────────────────────────────────

class FallbackLLMProvider(LLMProvider):
    """降级 LLM Provider（无 API 时使用）"""

    async def complete(self, prompt: str, config: LLMConfig | None = None) -> LLMResponse:
        logger.warning("Using fallback LLM provider")
        return LLMResponse(
            content=f"[Fallback] Processed: {prompt[:100]}...",
            model="fallback", tokens_used=0, cost_usd=0.0, latency_ms=100,
        )

    async def stream_complete(
        self,
        prompt: str,
        config: LLMConfig | None = None,
        on_thinking_start: Callable[[], Awaitable[None]] | None = None,
        on_thinking_delta: Callable[[str], Awaitable[None]] | None = None,
        on_thinking_end: Callable[[int], Awaitable[None]] | None = None,
    ) -> AsyncGenerator[str, None]:
        logger.warning("Using fallback LLM provider (streaming)")
        content = f"[Fallback] Processed: {prompt[:100]}..."
        for char in content:
            yield char
            await asyncio.sleep(0.01)

    async def chat_complete(
        self,
        messages: list[dict],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        last_message = messages[-1]["content"] if messages else ""
        return LLMResponse(
            content=f"[Fallback] Processed: {last_message[:100]}...",
            model="fallback", tokens_used=0, cost_usd=0.0, latency_ms=100,
        )


# ── 全局 Provider ──────────────────────────────────────────────

_global_llm_provider: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    global _global_llm_provider
    if _global_llm_provider is None:
        provider = LiteLLMProvider()
        if provider.is_available:
            _global_llm_provider = provider
        else:
            _global_llm_provider = FallbackLLMProvider()
    return _global_llm_provider


import asyncio
