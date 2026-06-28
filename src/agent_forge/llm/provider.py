"""LLM Provider 抽象层

为所有 LLM 调用注入统一的 system prompt，约束 thinking 格式与行为准则。
支持 tool_use（function calling）循环，让 LLM 在需要时主动调用技能。

Thinking 事件拆分（TASK-009）
------------------------------
stream_complete() 接受可选的 thinking 回调参数：
  on_thinking_start / on_thinking_delta / on_thinking_end

当检测到 <thinking> / </thinking> 标签边界时，自动切换推送目标：
  - thinking 内容 → on_thinking_delta（不走 yield）
  - 正文内容 → yield

Tracing（TASK-010）
--------------------
关键方法加了 @span 装饰器，自动采集耗时并输出结构化 JSON 日志。
无需手动打日志，只需保证调用方已开启 trace context。
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from agent_forge.tracing import get_current_span, span

logger = logging.getLogger("agent_forge.llm")


@dataclass
class ToolCall:
    id: str
    function_name: str
    function_args: dict[str, Any]

    def __repr__(self) -> str:
        return f"ToolCall(id={self.id}, function={self.function_name}({self.function_args!r}))"


DEFAULT_SYSTEM_PROMPT: str = (
    "你是一个多智能体协同框架的 AI 助手。请遵循以下回答规范：\n"
    "\n"
    "## 思考过程\n"
    "- 如需推理分析，请在 <thinking>...</thinking> 标签内完成。\n"
    "- 思考过程请使用**平铺直叙的段落文字**，不要使用 markdown 标题（### 等）。\n"
    "- 如需列举要点，请使用 - 短横线列表或 1. 2. 数字列表。\n"
    "\n"
    "## 正文回复\n"
    "- 在 <thinking> 标签之外输出面向用户的正式回复。\n"
    "- 可以使用完整的 markdown 格式（标题、列表、表格等）。\n"
)


def _build_messages(prompt: str, system_prompt: str) -> list[dict]:
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]


@dataclass
class LLMConfig:
    model: str
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 60


@dataclass
class LLMResponse:
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
    @abstractmethod
    async def complete(self, prompt: str, config: LLMConfig | None = None) -> LLMResponse: ...

    @abstractmethod
    async def stream_complete(
        self,
        prompt: str,
        config: LLMConfig | None = None,
        on_thinking_start: Callable[[], Awaitable[None]] | None = None,
        on_thinking_delta: Callable[[str], Awaitable[None]] | None = None,
        on_thinking_end: Callable[[int], Awaitable[None]] | None = None,
    ) -> AsyncGenerator[str, None]: ...

    @abstractmethod
    async def chat_complete(self, messages: list[dict], config: LLMConfig | None = None) -> LLMResponse: ...


class LiteLLMProvider(LLMProvider):
    """LiteLLM Provider，关键方法均加了 @span 自动 tracing"""

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

    @span("llm.complete")
    async def complete(self, prompt: str, config: LLMConfig | None = None) -> LLMResponse:
        if not self.is_available:
            return LLMResponse(content="LiteLLM not available", model="none",
                               tokens_used=0, cost_usd=0.0, latency_ms=0)
        config = config or LLMConfig(model="gpt-4o")
        t0 = time.time()
        messages = _build_messages(prompt, DEFAULT_SYSTEM_PROMPT)
        try:
            response = await self.litellm.acompletion(
                model=config.model, messages=messages,
                temperature=config.temperature, max_tokens=config.max_tokens,
            )
            result = LLMResponse(
                content=response["choices"][0]["message"]["content"],
                model=config.model,
                tokens_used=response.get("usage", {}).get("total_tokens", 0),
                cost_usd=response.get("usage", {}).get("cost", 0.0),
                latency_ms=int((time.time() - t0) * 1000),
            )
            _tag_tokens(result)
            return result
        except Exception as e:
            logger.error("LiteLLM complete error: %s", e)
            raise

    @span("llm.chat_complete")
    async def chat_complete(self, messages: list[dict], config: LLMConfig | None = None) -> LLMResponse:
        if not self.is_available:
            return LLMResponse(content="LiteLLM not available", model="none",
                               tokens_used=0, cost_usd=0.0, latency_ms=0)
        config = config or LLMConfig(model="gpt-4o")
        t0 = time.time()
        try:
            response = await self.litellm.acompletion(
                model=config.model, messages=messages,
                temperature=config.temperature, max_tokens=config.max_tokens,
            )
            result = LLMResponse(
                content=response["choices"][0]["message"]["content"],
                model=config.model,
                tokens_used=response.get("usage", {}).get("total_tokens", 0),
                cost_usd=response.get("usage", {}).get("cost", 0.0),
                latency_ms=int((time.time() - t0) * 1000),
            )
            _tag_tokens(result)
            return result
        except Exception as e:
            logger.error("LiteLLM chat_complete error: %s", e)
            raise

    @span("llm.tool_use_complete")
    async def tool_use_complete(
        self,
        messages: list[dict],
        tools: list[dict],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        """工具调用决策（非流式）。耗时通常是整个请求最大的单点。"""
        if not self.is_available:
            return LLMResponse(content="LiteLLM not available", model="none",
                               tokens_used=0, cost_usd=0.0, latency_ms=0)
        config = config or LLMConfig(model="gpt-4o")
        t0 = time.time()

        # 把工具数量写入 span tags，便于排查"工具太多导致 prompt 膨胀"
        sp = get_current_span()
        if sp:
            sp.tags.update({"model": config.model, "tools": len(tools), "msgs": len(messages)})

        try:
            response: Any = await self.litellm.acompletion(
                model=config.model, messages=messages,
                temperature=config.temperature, max_tokens=config.max_tokens,
                tools=tools,
            )
            latency_ms = int((time.time() - t0) * 1000)
            choice = response["choices"][0]["message"]
            tool_calls: list[ToolCall] = []
            for tc in (choice.get("tool_calls") or []):
                tool_calls.append(ToolCall(
                    id=tc["id"],
                    function_name=tc["function"]["name"],
                    function_args=json.loads(tc["function"]["arguments"]),
                ))
            result = LLMResponse(
                content=choice.get("content") or "",
                model=config.model,
                tokens_used=response.get("usage", {}).get("total_tokens", 0),
                cost_usd=response.get("usage", {}).get("cost", 0.0),
                latency_ms=latency_ms,
                _tool_calls=tool_calls or None,
            )
            _tag_tokens(result)
            if sp:
                sp.tags["has_tool_calls"] = result.has_tool_calls
                sp.tags["tool_names"] = [tc.function_name for tc in tool_calls]
            return result
        except Exception as e:
            logger.error("LiteLLM tool_use_complete error: %s", e)
            raise

    # stream_complete 本身是 async generator，不能用 @span 直接包装；
    # 在内部通过 get_tracer().start_span 手动开 span
    async def stream_complete(
        self,
        prompt: str,
        config: LLMConfig | None = None,
        on_thinking_start: Callable[[], Awaitable[None]] | None = None,
        on_thinking_delta: Callable[[str], Awaitable[None]] | None = None,
        on_thinking_end: Callable[[int], Awaitable[None]] | None = None,
        system_prompt: str | None = None,
    ) -> AsyncGenerator[str, None]:
        if not self.is_available:
            yield "LiteLLM not available"
            return
        config = config or LLMConfig(model="gpt-4o")
        messages = _build_messages(prompt, system_prompt or DEFAULT_SYSTEM_PROMPT)

        from agent_forge.tracing import get_tracer
        async with get_tracer().start_span(
            "llm.stream_complete",
            tags={"model": config.model, "prompt_len": len(prompt)},
        ) as sp:
            chunk_count = 0
            first_chunk_ms: int | None = None
            t0 = time.monotonic()
            try:
                response = await self.litellm.acompletion(
                    model=config.model, messages=messages,
                    temperature=config.temperature, max_tokens=config.max_tokens,
                    stream=True,
                )
                async for chunk in _stream_with_thinking(
                    response,
                    on_thinking_start=on_thinking_start,
                    on_thinking_delta=on_thinking_delta,
                    on_thinking_end=on_thinking_end,
                ):
                    if chunk:
                        if first_chunk_ms is None:
                            first_chunk_ms = int((time.monotonic() - t0) * 1000)
                        chunk_count += 1
                        yield chunk
            except Exception as e:
                logger.error("LiteLLM stream_complete error: %s", e)
                yield f"Error: {e}"
            finally:
                sp.tags.update({
                    "chunks": chunk_count,
                    "ttfc_ms": first_chunk_ms,   # time-to-first-chunk，关键延迟指标
                })

    @span("llm.tool_use_stream")
    async def tool_use_stream(
        self,
        messages: list[dict],
        tools: list[dict],
        config: LLMConfig | None = None,
    ) -> AsyncGenerator[str | ToolCall, None]:
        if not self.is_available:
            yield "LiteLLM not available"
            return
        config = config or LLMConfig(model="gpt-4o")
        try:
            response = await self.litellm.acompletion(
                model=config.model, messages=messages,
                temperature=config.temperature, max_tokens=config.max_tokens,
                tools=tools, stream=True,
            )
            pending: dict[str, ToolCall] = {}
            async for chunk in response:
                delta = chunk["choices"][0].get("delta", {})
                reasoning = delta.get("reasoning") or ""
                if reasoning:
                    yield reasoning
                content = delta.get("content") or ""
                if content:
                    yield content
                for tc in (delta.get("tool_calls") or []):
                    tc_id = tc.get("id", "")
                    if tc_id not in pending:
                        pending[tc_id] = ToolCall(id=tc_id, function_name="", function_args={})
                    p = pending[tc_id]
                    fn = tc.get("function", {})
                    if fn.get("name"):
                        p.function_name = fn["name"]
                    if fn.get("arguments"):
                        try:
                            p.function_args = json.loads(
                                json.dumps(p.function_args) + fn["arguments"].lstrip(","))
                        except json.JSONDecodeError:
                            pass
            for tc in pending.values():
                if tc.function_name:
                    yield tc
        except Exception as e:
            logger.error("LiteLLM tool_use_stream error: %s", e)
            yield f"Error: {e}"


# ── Thinking 流式解析器 ───────────────────────────────────────

async def _stream_with_thinking(
    litellm_response: Any,
    on_thinking_start: Callable[[], Awaitable[None]] | None,
    on_thinking_delta: Callable[[str], Awaitable[None]] | None,
    on_thinking_end: Callable[[int], Awaitable[None]] | None,
) -> AsyncGenerator[str, None]:
    """从 LiteLLM 流式响应中拆分 thinking 和正文。

    两类 thinking 来源：
      1. delta.reasoning（原生 reasoning 字段，o1/Claude compat）
      2. delta.content 中内嵌 <thinking>...</thinking> 标签（DeepSeek-R1 等）

    yield 只输出正文；thinking 通过回调推送，两者严格互斥。
    """
    in_thinking = False
    thinking_start_time: float = 0.0
    tag_buffer = ""
    OPEN_TAG  = "<thinking>"
    CLOSE_TAG = "</thinking>"

    async def _start() -> None:
        nonlocal in_thinking, thinking_start_time
        if not in_thinking:
            in_thinking = True
            thinking_start_time = time.time()
            if on_thinking_start:
                await on_thinking_start()

    async def _end() -> None:
        nonlocal in_thinking
        if in_thinking:
            in_thinking = False
            duration_ms = int((time.time() - thinking_start_time) * 1000)
            if on_thinking_end:
                await on_thinking_end(duration_ms)

    async for chunk in litellm_response:
        delta = chunk["choices"][0].get("delta", {})

        # 来源1：原生 reasoning 字段
        reasoning = delta.get("reasoning") or ""
        if reasoning:
            await _start()
            if on_thinking_delta:
                await on_thinking_delta(reasoning)
            continue

        content = delta.get("content") or ""
        if not content:
            continue

        text = tag_buffer + content
        tag_buffer = ""

        while text:
            if in_thinking:
                idx = text.find(CLOSE_TAG)
                if idx == -1:
                    slen = _suffix_match(text, CLOSE_TAG)
                    if slen:
                        if on_thinking_delta and text[:-slen]:
                            await on_thinking_delta(text[:-slen])
                        tag_buffer = text[-slen:]
                    else:
                        if on_thinking_delta:
                            await on_thinking_delta(text)
                    break
                else:
                    if on_thinking_delta and text[:idx]:
                        await on_thinking_delta(text[:idx])
                    await _end()
                    text = text[idx + len(CLOSE_TAG):].lstrip("\n")
            else:
                idx = text.find(OPEN_TAG)
                if idx == -1:
                    slen = _suffix_match(text, OPEN_TAG)
                    if slen:
                        if text[:-slen]:
                            yield text[:-slen]
                        tag_buffer = text[-slen:]
                    else:
                        yield text
                    break
                else:
                    if text[:idx]:
                        yield text[:idx]
                    await _start()
                    text = text[idx + len(OPEN_TAG):]

    if in_thinking:
        if tag_buffer and on_thinking_delta:
            await on_thinking_delta(tag_buffer)
        await _end()
    elif tag_buffer:
        yield tag_buffer


def _suffix_match(text: str, tag: str) -> int:
    """返回 text 末尾与 tag 前缀匹配的最大长度，处理跨 chunk 标签拆断。"""
    for length in range(min(len(tag) - 1, len(text)), 0, -1):
        if text.endswith(tag[:length]):
            return length
    return 0


def _tag_tokens(result: LLMResponse) -> None:
    """把 token 用量写入当前 span tags（有 span 时才写）。"""
    sp = get_current_span()
    if sp:
        sp.tags.update({"model": result.model, "tokens": result.tokens_used})


# ── Fallback Provider ──────────────────────────────────────────

class FallbackLLMProvider(LLMProvider):

    async def complete(self, prompt: str, config: LLMConfig | None = None) -> LLMResponse:
        return LLMResponse(content=f"[Fallback] {prompt[:80]}", model="fallback",
                           tokens_used=0, cost_usd=0.0, latency_ms=0)

    async def stream_complete(
        self,
        prompt: str,
        config: LLMConfig | None = None,
        on_thinking_start: Callable[[], Awaitable[None]] | None = None,
        on_thinking_delta: Callable[[str], Awaitable[None]] | None = None,
        on_thinking_end: Callable[[int], Awaitable[None]] | None = None,
    ) -> AsyncGenerator[str, None]:
        for ch in f"[Fallback] {prompt[:80]}":
            yield ch
            await asyncio.sleep(0.005)

    async def chat_complete(self, messages: list[dict], config: LLMConfig | None = None) -> LLMResponse:
        last = messages[-1]["content"] if messages else ""
        return LLMResponse(content=f"[Fallback] {last[:80]}", model="fallback",
                           tokens_used=0, cost_usd=0.0, latency_ms=0)


# ── 全局单例 ──────────────────────────────────────────────────

_global_llm_provider: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    global _global_llm_provider
    if _global_llm_provider is None:
        p = LiteLLMProvider()
        _global_llm_provider = p if p.is_available else FallbackLLMProvider()
    return _global_llm_provider
