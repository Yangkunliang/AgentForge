"""
agent_forge.sandbox.factory
=============================
沙箱 Provider 工厂：根据配置返回对应 SandboxExecutor 实例。

支持 Provider
-------------
- mock         → MockSandboxExecutor       （本地开发 / 单元测试）
- docker       → DockerSandboxExecutor     （可信代码，容器级隔离）
- cubesandbox_e2b   → CubeSandboxE2BExecutor   （E2B SDK，推荐）
- cubesandbox_api   → CubeSandboxAPIExecutor   （REST API，精细控制）

用法
----
    from agent_forge.sandbox.factory import SandboxProviderFactory
    from agent_forge.config import settings

    executor = SandboxProviderFactory.create(
        provider=settings.cube_sandbox.default_provider,
        url=settings.cube_sandbox.url,
        api_key=settings.cube_sandbox.api_key,
        template_id=settings.cube_sandbox.template_id,
    )
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class SandboxProviderFactory:
    """沙箱 Provider 工厂。

    Args:
        provider:     Provider 名称，来自 CUBE_SANDBOX_DEFAULT_PROVIDER
        url:          CubeSandbox API 地址（仅 cubesandbox_* provider 需要）
        api_key:      API Key（仅 cubesandbox_* provider 需要）
        template_id:  默认模板 ID
    """

    @staticmethod
    def create(
        provider: str = "mock",
        url: str = "http://127.0.0.1:3000",
        api_key: str = "",
        template_id: str = "",
    ):
        """根据 provider 名称返回对应的 SandboxExecutor 实例。

        Args:
            provider:     枚举值：mock | docker | cubesandbox_e2b | cubesandbox_api
            url:          CubeSandbox 集群地址
            api_key:      API Key
            template_id:  默认模板 ID

        Returns:
            实现了 SandboxExecutor Protocol 的实例
        """
        if provider == "mock":
            from agent_forge.sandbox.mock import MockSandboxExecutor

            logger.info("SandboxProviderFactory: using MockSandboxExecutor")
            return MockSandboxExecutor()

        if provider == "docker":
            from agent_forge.sandbox.docker import DockerSandboxExecutor

            logger.info("SandboxProviderFactory: using DockerSandboxExecutor")
            return DockerSandboxExecutor()

        if provider in ("cubesandbox_e2b", "cubesandbox_api"):
            if provider == "cubesandbox_e2b":
                from agent_forge.sandbox.cubesandbox import CubeSandboxE2BExecutor

                logger.info(
                    "SandboxProviderFactory: using CubeSandboxE2BExecutor (url=%s)",
                    url,
                )
                return CubeSandboxE2BExecutor(
                    api_url=url, api_key=api_key, template_id=template_id
                )

            # cubesandbox_api
            from agent_forge.sandbox.cubesandbox import CubeSandboxAPIExecutor

            logger.info(
                "SandboxProviderFactory: using CubeSandboxAPIExecutor (url=%s)",
                url,
            )
            return CubeSandboxAPIExecutor(base_url=url, api_key=api_key)

        # 未知 provider，降级到 mock
        logger.warning(
            "SandboxProviderFactory: unknown provider %r, falling back to mock",
            provider,
        )
        from agent_forge.sandbox.mock import MockSandboxExecutor

        return MockSandboxExecutor()
