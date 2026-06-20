"""Harness Governance 测试"""

import pytest

from agent_forge.harness import (
    CircuitBreaker,
    RetryHandler,
    GovernanceManager,
    RecoverableError,
    UnrecoverableError,
)


class TestCircuitBreaker:
    """熔断器测试"""

    def test_circuit_breaker_initial_state(self):
        """测试熔断器初始状态"""
        breaker = CircuitBreaker("test")
        assert not breaker.is_open

    @pytest.mark.asyncio
    async def test_circuit_breaker_record_failure(self):
        """测试记录失败"""
        breaker = CircuitBreaker("test")

        async def failing_func():
            raise Exception("test error")

        with pytest.raises(Exception):
            await breaker.call(failing_func)


class TestRetryHandler:
    """重试处理器测试"""

    def test_is_recoverable(self):
        """测试可恢复错误判断"""
        handler = RetryHandler()

        assert handler.is_recoverable(ConnectionError())
        assert handler.is_recoverable(TimeoutError())
        assert handler.is_recoverable(RecoverableError())
        assert not handler.is_recoverable(UnrecoverableError())
        assert not handler.is_recoverable(ValueError())


class TestGovernanceManager:
    """治理管理器测试"""

    @pytest.mark.asyncio
    async def test_execute_with_governance(self):
        """测试带治理的执行"""
        manager = GovernanceManager()

        async def success_func():
            return {"result": "success"}

        result = await manager.execute_with_governance(success_func)
        assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_execute_with_fallback(self):
        """测试降级处理"""
        manager = GovernanceManager()

        async def failing_func():
            raise UnrecoverableError("test")

        async def fallback_func():
            return {"result": "fallback"}

        with pytest.raises(UnrecoverableError):
            await manager.execute_with_governance(failing_func, fallback_func)