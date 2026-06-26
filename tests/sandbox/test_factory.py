"""
tests/sandbox/test_factory.py
==============================
SandboxProviderFactory 单元测试

覆盖场景
--------
- 各 provider 路由：mock / docker / cubesandbox_e2b / cubesandbox_api
- 未知 provider 降级为 mock
- 默认 provider 为 mock
"""

import pytest


class TestSandboxProviderFactory:
    """测试 SandboxProviderFactory.create() 的路由逻辑。"""

    def test_create_mock_returns_mock_executor(self):
        from agent_forge.sandbox.factory import SandboxProviderFactory
        from agent_forge.sandbox.mock import MockSandboxExecutor

        result = SandboxProviderFactory.create(provider="mock")
        assert isinstance(result, MockSandboxExecutor)

    def test_create_docker_returns_docker_executor(self):
        from agent_forge.sandbox.factory import SandboxProviderFactory
        from agent_forge.sandbox.docker import DockerSandboxExecutor

        result = SandboxProviderFactory.create(provider="docker")
        assert isinstance(result, DockerSandboxExecutor)

    def test_create_cubesandbox_e2b_returns_e2b_executor(self):
        from agent_forge.sandbox.factory import SandboxProviderFactory
        from agent_forge.sandbox.cubesandbox import CubeSandboxE2BExecutor

        result = SandboxProviderFactory.create(
            provider="cubesandbox_e2b",
            url="http://127.0.0.1:3000",
            api_key="test-key",
            template_id="tpl-test",
        )
        assert isinstance(result, CubeSandboxE2BExecutor)
        assert result._api_url == "http://127.0.0.1:3000"
        assert result._api_key == "test-key"
        assert result._template_id == "tpl-test"

    def test_create_cubesandbox_api_returns_api_executor(self):
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

    def test_create_unknown_provider_fallback_to_mock(self):
        from agent_forge.sandbox.factory import SandboxProviderFactory
        from agent_forge.sandbox.mock import MockSandboxExecutor

        result = SandboxProviderFactory.create(provider="nonexistent")
        assert isinstance(result, MockSandboxExecutor)

    def test_create_default_provider_is_mock(self):
        from agent_forge.sandbox.factory import SandboxProviderFactory
        from agent_forge.sandbox.mock import MockSandboxExecutor

        # 不传 provider，使用默认值
        result = SandboxProviderFactory.create()
        assert isinstance(result, MockSandboxExecutor)

    def test_create_e2b_sets_env_vars(self):
        from agent_forge.sandbox.factory import SandboxProviderFactory

        # 保存原始值以便恢复
        original_e2b_domain = __import__("os").environ.pop("E2B_DOMAIN", None)
        original_e2b_dp = __import__("os").environ.pop("E2B_DATA_PLANE_URL", None)

        try:
            SandboxProviderFactory.create(
                provider="cubesandbox_e2b",
                url="http://example.com",
                api_key="k",
            )
            assert __import__("os").environ.get("E2B_DOMAIN") == ""
            assert __import__("os").environ.get("E2B_DATA_PLANE_URL") == "http://example.com"
        finally:
            if original_e2b_domain is not None:
                __import__("os").environ["E2B_DOMAIN"] = original_e2b_domain
            if original_e2b_dp is not None:
                __import__("os").environ["E2B_DATA_PLANE_URL"] = original_e2b_dp
            else:
                __import__("os").environ.pop("E2B_DOMAIN", None)
                __import__("os").environ.pop("E2B_DATA_PLANE_URL", None)
