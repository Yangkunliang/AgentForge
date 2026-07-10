"""Harness Governance 测试"""

import pytest

from agent_forge.harness import (
    CircuitBreaker,
    RetryHandler,
    GovernanceManager,
    RecoverableError,
    UnrecoverableError,
)
from agent_forge.governance.policy import GovernancePolicy


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


class TestGovernancePolicy:
    """统一人工确认策略测试"""

    def test_stage_confirmation_policy_returns_context(self):
        decision = GovernancePolicy().evaluate_stage_confirmation(
            stage_id="analysis",
            stage_name="需求分析",
            confirmation_gate="prd_review",
        )

        assert decision.decision == "require_confirmation"
        assert decision.confirmation_type == "prd_review"
        assert decision.risk_level == "medium"
        assert "需求" in decision.reason
        assert decision.impact_scope == [
            {
                "type": "pipeline_stage",
                "id": "analysis",
                "label": "需求分析",
            }
        ]
        assert decision.audit_payload()["confirmation_type"] == "prd_review"

    def test_delivery_policy_requires_confirmation_before_write(self):
        decision = GovernancePolicy().evaluate_delivery_confirmation(
            channel="local",
            target_path="src/main.py",
            artifact_id="artifact-1",
            mount_id="mount-1",
            confirmed=False,
        )

        assert decision.decision == "require_confirmation"
        assert decision.confirmation_type == "delivery_write"
        assert decision.risk_level == "high"
        assert decision.audit_payload()["reason_code"] == "missing_confirmation"
        assert decision.impact_scope == [
            {"type": "artifact", "id": "artifact-1", "label": "artifact-1"},
            {"type": "mount", "id": "mount-1", "label": "mount-1"},
            {"type": "path", "id": "src/main.py", "label": "src/main.py"},
        ]

    def test_skill_policy_requires_confirmation_for_high_risk_permission(self):
        decision = GovernancePolicy().evaluate_skill_call(
            skill_name="external-shell",
            tool_name="shell_tool",
            permissions=["shell"],
            confirmed=False,
        )

        assert decision.decision == "require_confirmation"
        assert decision.confirmation_type == "skill_high_risk"
        assert decision.risk_level == "high"
        assert decision.audit_payload()["permissions"] == ["shell"]
