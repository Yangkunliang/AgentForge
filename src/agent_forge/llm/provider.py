"""LLM Provider 抽象层"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, AsyncGenerator

if TYPE_CHECKING:
    from litellm import ModelResponse

logger = logging.getLogger("agent_forge.llm")


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


class LLMProvider(ABC):
    """LLM Provider 基类"""

    @abstractmethod
    async def complete(self, prompt: str, config: LLMConfig | None = None) -> LLMResponse:
        """同步完成"""
        pass

    @abstractmethod
    async def stream_complete(
        self,
        prompt: str,
        config: LLMConfig | None = None,
    ) -> AsyncGenerator[str, None]:
        """流式完成"""
        pass

    @abstractmethod
    async def chat_complete(
        self,
        messages: list[dict],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        """聊天完成"""
        pass


class LiteLLMProvider(LLMProvider):
    """LiteLLM Provider（支持多种 LLM）"""

    def __init__(self):
        try:
            import litellm
            from agent_forge.config import settings
            self.litellm = litellm
            self._available = True
            # 如果配置了自定义 base_url，全局注入（适用于 OpenAI-compatible 接口，如百炼）
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
        """同步完成"""
        if not self.is_available:
            return LLMResponse(
                content="LiteLLM not available",
                model="none",
                tokens_used=0,
                cost_usd=0.0,
                latency_ms=0,
            )

        config = config or LLMConfig(model="gpt-4o")

        import time
        start_time = time.time()

        try:
            response = await self.litellm.acompletion(
                model=config.model,
                messages=[{"role": "user", "content": prompt}],
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
    ) -> AsyncGenerator[str, None]:
        """流式完成

        收集所有流式 chunk，将 reasoning/thinking 内容用 <thinking>...</thinking>
        包裹后拼接到结果开头。这样前端 parseThinking() 能正确提取并渲染思考过程。

        不同模型的 reasoning delta 字段名不同：
          - OpenAI o1/o3 系列: delta["reasoning"]
          - Claude (via OpenAI compat): delta["reasoning"] 或 delta["cache_control"]
          - 普通模型: 只有 delta["content"]，无 reasoning
        """
        if not self.is_available:
            yield "LiteLLM not available"
            return

        config = config or LLMConfig(model="gpt-4o")

        try:
            response = await self.litellm.acompletion(
                model=config.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                stream=True,
            )

            reasoning_parts: list[str] = []
            content_parts: list[str] = []

            async for chunk in response:
                delta = chunk["choices"][0].get("delta", {})

                # 收集 reasoning（不同厂商用不同字段名）
                reasoning = delta.get("reasoning") or ""
                if reasoning:
                    reasoning_parts.append(reasoning)

                # 收集可见回复内容
                content = delta.get("content") or ""
                if content:
                    content_parts.append(content)

            # 拼接完整内容：thinking + 主体回复
            full_reasoning = "".join(reasoning_parts)
            full_content = "".join(content_parts)

            # 如果有 reasoning，用标签包裹后拼在前面
            if full_reasoning:
                logger.info(
                    "stream_complete: collected reasoning content, "
                    "reasoning_len=%d, body_len=%d",
                    len(full_reasoning),
                    len(full_content),
                )
                yield f"<thinking>\n{full_reasoning.strip()}\n</thinking>\n\n{full_content}"
            else:
                yield full_content
        except Exception as e:
            logger.error(f"LiteLLM stream error: {e}")
            yield f"Error: {e}"

    async def chat_complete(
        self,
        messages: list[dict],
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        """聊天完成"""
        if not self.is_available:
            return LLMResponse(
                content="LiteLLM not available",
                model="none",
                tokens_used=0,
                cost_usd=0.0,
                latency_ms=0,
            )

        config = config or LLMConfig(model="gpt-4o")

        import time
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


class FallbackLLMProvider(LLMProvider):
    """降级 LLM Provider（无 API 时使用）"""

    async def complete(self, prompt: str, config: LLMConfig | None = None) -> LLMResponse:
        """返回降级响应"""
        logger.warning("Using fallback LLM provider")
        return LLMResponse(
            content=f"[Fallback] Processed: {prompt[:100]}...",
            model="fallback",
            tokens_used=0,
            cost_usd=0.0,
            latency_ms=100,
        )

    async def stream_complete(
        self,
        prompt: str,
        config: LLMConfig | None = None,
    ) -> AsyncGenerator[str, None]:
        """流式降级响应"""
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
        """聊天降级响应"""
        last_message = messages[-1]["content"] if messages else ""
        return LLMResponse(
            content=f"[Fallback] Processed: {last_message[:100]}...",
            model="fallback",
            tokens_used=0,
            cost_usd=0.0,
            latency_ms=100,
        )


# 全局 LLM Provider
_global_llm_provider: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    """获取全局 LLM Provider"""
    global _global_llm_provider
    if _global_llm_provider is None:
        provider = LiteLLMProvider()
        if provider.is_available:
            _global_llm_provider = provider
        else:
            _global_llm_provider = FallbackLLMProvider()
    return _global_llm_provider


# 兼容导入
import asyncio