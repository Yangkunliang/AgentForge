"""Harness Layer 4: Governance - 重试、熔断、降级"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, TypeVar, Awaitable, Callable

import pybreaker
import tenacity
from tenacity import RetryCallState

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("agent_forge.harness.governance")


# 可恢复错误类型
class RecoverableError(Exception):
    """可恢复的错误（可以重试）"""
    pass


class UnrecoverableError(Exception):
    """不可恢复的错误（不应重试）"""
    pass


# 熔断器配置
CIRCUIT_BREAKER_CONFIG = {
    "fail_max": 5,  # 10 次窗口中 5 次失败 = 50% 触发
    "reset_timeout": 30,  # 30s 后半开
}


class CircuitBreaker:
    """熔断器包装器"""

    def __init__(self, name: str = "default"):
        self.name = name
        self.breaker = pybreaker.CircuitBreaker(
            fail_max=CIRCUIT_BREAKER_CONFIG["fail_max"],
            reset_timeout=CIRCUIT_BREAKER_CONFIG["reset_timeout"],
        )
        self._is_open = False

    @property
    def is_open(self) -> bool:
        """熔断器是否开启"""
        return self.breaker.current_state == pybreaker.STATE_OPEN

    @property
    def is_half_open(self) -> bool:
        """熔断器是否半开"""
        return self.breaker.current_state == pybreaker.STATE_HALF_OPEN

    async def call(self, func: Callable, *args, **kwargs):
        """使用熔断器调用函数"""
        try:
            result = await self.breaker.call_async(func, *args, **kwargs)
            return result
        except pybreaker.CircuitBreakerError:
            logger.warning(f"Circuit breaker '{self.name}' is OPEN, request rejected")
            self._is_open = True
            raise
        except Exception as e:
            logger.error(f"Circuit breaker '{self.name}' recorded failure: {e}")
            raise


# 重试配置
RETRY_CONFIG = {
    "stop_after_attempt": 3,
    "wait_exponential_multiplier": 1000,  # 1s
    "wait_exponential_max": 4000,  # 4s
}


class RetryHandler:
    """重试处理器"""

    def __init__(self):
        self.retry_config = RETRY_CONFIG

    def is_recoverable(self, error: Exception) -> bool:
        """判断错误是否可恢复"""
        # 网络错误、临时故障可恢复
        recoverable_types = (
            ConnectionError,
            TimeoutError,
            RecoverableError,
        )
        return isinstance(error, recoverable_types)

    def before_retry(self, retry_state: RetryCallState) -> None:
        """重试前回调"""
        attempt = retry_state.attempt_number
        wait_time = retry_state.next_action.sleep if retry_state.next_action else 0
        logger.info(f"Retry attempt {attempt}, waiting {wait_time}s")

    def after_retry(self, retry_state: RetryCallState) -> None:
        """重试成功后回调"""
        attempt = retry_state.attempt_number
        logger.info(f"Retry succeeded after {attempt} attempts")


def with_retry(func: Callable[..., Awaitable]):
    """重试装饰器"""
    handler = RetryHandler()

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(RETRY_CONFIG["stop_after_attempt"]),
        wait=tenacity.wait_exponential(
            multiplier=RETRY_CONFIG["wait_exponential_multiplier"] / 1000,
            max=RETRY_CONFIG["wait_exponential_max"] / 1000,
        ),
        retry=tenacity.retry_if_exception(handler.is_recoverable),
        before_sleep=handler.before_retry,
    )
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)

    return wrapper


class GovernanceManager:
    """治理管理器（整合重试、熔断、降级）"""

    def __init__(self, circuit_breaker_name: str = "default"):
        self.circuit_breaker = CircuitBreaker(circuit_breaker_name)
        self.retry_handler = RetryHandler()

    async def execute_with_governance(
        self,
        func: Callable[..., Awaitable],
        fallback_func: Callable | None = None,
        *args,
        **kwargs,
    ):
        """带治理的执行（重试 + 熔断 + 降级）"""
        # 1. 检查熔断器
        if self.circuit_breaker.is_open:
            logger.warning(f"Circuit breaker is OPEN, using fallback for {func.__name__}")
            if fallback_func:
                return await fallback_func()
            raise UnrecoverableError("Circuit breaker is OPEN")

        try:
            # 2. 带重试执行
            result = await self._execute_with_retry(func, *args, **kwargs)
            return result

        except pybreaker.CircuitBreakerError:
            # 3. 熔断器开启，使用降级
            logger.warning(f"Circuit breaker triggered for {func.__name__}")
            if fallback_func:
                return await fallback_func()
            raise

        except Exception as e:
            # 4. 其他错误
            if not self.retry_handler.is_recoverable(e):
                logger.error(f"Unrecoverable error in {func.__name__}: {e}")
                raise
            raise

    async def _execute_with_retry(
        self,
        func: Callable[..., Awaitable],
        *args,
        **kwargs,
    ):
        """带重试的执行"""
        last_error = None
        max_attempts = RETRY_CONFIG["stop_after_attempt"]

        for attempt in range(1, max_attempts + 1):
            try:
                return await self.circuit_breaker.call(func, *args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < max_attempts and self.retry_handler.is_recoverable(e):
                    wait_time = RETRY_CONFIG["wait_exponential_multiplier"] * (2 ** (attempt - 1)) / 1000
                    wait_time = min(wait_time, RETRY_CONFIG["wait_exponential_max"] / 1000)
                    logger.info(f"Attempt {attempt} failed, retrying in {wait_time}s: {e}")
                    import asyncio
                    await asyncio.sleep(wait_time)
                else:
                    break

        raise last_error


# 全局治理管理器
_global_governance_manager: GovernanceManager | None = None


def get_governance_manager() -> GovernanceManager:
    """获取全局治理管理器"""
    global _global_governance_manager
    if _global_governance_manager is None:
        _global_governance_manager = GovernanceManager()
    return _global_governance_manager