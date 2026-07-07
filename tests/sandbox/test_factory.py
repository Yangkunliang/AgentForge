"""
tests/sandbox/test_factory.py
==============================
SandboxProviderFactory 单元测试

覆盖场景
--------
- provider 路由：cubesandbox_e2b / cubesandbox_api
- cubesandbox_api 透传 CUBE_SANDBOX_API_KEY
- 已移除 provider 明确报错
- 默认 provider 为 cubesandbox_e2b
"""

import pytest


class TestSandboxProviderFactory:
    """测试 SandboxProviderFactory.create() 的路由逻辑。"""

    def test_create_default_provider_is_e2b_executor(self, monkeypatch):
        from agent_forge.sandbox.factory import SandboxProviderFactory
        from agent_forge.sandbox.cubesandbox import CubeSandboxE2BExecutor

        monkeypatch.setenv("E2B_API_KEY", "test-e2b-key")

        result = SandboxProviderFactory.create()
        assert isinstance(result, CubeSandboxE2BExecutor)

    def test_create_cubesandbox_api_returns_api_executor_with_api_key(self):
        from agent_forge.sandbox.factory import SandboxProviderFactory
        from agent_forge.sandbox.cubesandbox import CubeSandboxAPIExecutor

        result = SandboxProviderFactory.create(
            provider="cubesandbox_api",
            url="http://127.0.0.1:3000",
            api_key="test-key",
        )
        assert isinstance(result, CubeSandboxAPIExecutor)
        assert result._base_url == "http://127.0.0.1:3000"
        assert result._api_key == "test-key"

    @pytest.mark.parametrize("provider", ["mock", "docker", "nonexistent"])
    def test_create_removed_or_unknown_provider_raises_value_error(self, provider):
        from agent_forge.sandbox.factory import SandboxProviderFactory

        with pytest.raises(ValueError):
            SandboxProviderFactory.create(provider=provider)
