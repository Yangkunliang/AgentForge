"""
agent_forge.sandbox.factory
=============================
沙箱 Provider 工厂：根据配置返回对应 SandboxExecutor 实例。

支持的 Provider
---------------
- cubesandbox_e2b   → CubeSandboxE2BExecutor（E2B SDK v1，推荐）
- cubesandbox_api   → CubeSandboxAPIExecutor（REST API，精细控制）

不再支持的 Provider
-------------------
- mock   已移除。开发环境直接使用 E2B 云服务（设置 E2B_API_KEY 即可）。
- docker 已移除。隔离由 E2B/CubeSandbox 负责，不需要本地 Docker。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class SandboxProviderFactory:
    """沙箱 Provider 工厂。

    Args:
        provider:     Provider 名称，来自 CUBE_SANDBOX_DEFAULT_PROVIDER
        api_key:      E2B API Key（E2B 云服务或自部署 CubeSandbox 均需要）
        url:          自部署 CubeSandbox 地址（不设置则使用 E2B 云）
        template_id:  默认模板 ID
    """

    @staticmethod
    def create(
        provider: str = "cubesandbox_e2b",
        url: str = "",
        template_id: str = "",
    ):
        """根据 provider 名称返回对应的 SandboxExecutor 实例。

        E2B_API_KEY 由各 Executor 直接从环境变量读取，不经由此处传递。

        Args:
            provider:     cubesandbox_e2b | cubesandbox_api
            url:          自部署 CubeSandbox 地址（空字符串 = 使用 E2B 云）
            template_id:  默认模板 ID
        """
        if provider == "cubesandbox_e2b":
            from agent_forge.sandbox.cubesandbox import CubeSandboxE2BExecutor  # noqa: PLC0415

            logger.info(
                "SandboxProviderFactory: using CubeSandboxE2BExecutor (url=%r)",
                url or "E2B cloud",
            )
            return CubeSandboxE2BExecutor(
                api_url=url or None,
                template_id=template_id or None,
            )

        if provider == "cubesandbox_api":
            from agent_forge.sandbox.cubesandbox import CubeSandboxAPIExecutor  # noqa: PLC0415

            logger.info(
                "SandboxProviderFactory: using CubeSandboxAPIExecutor (url=%s)", url
            )
            return CubeSandboxAPIExecutor(base_url=url, api_key=api_key)

        raise ValueError(
            f"SandboxProviderFactory: 不支持的 provider {provider!r}。"
            f"支持的选项：cubesandbox_e2b | cubesandbox_api。"
            f"mock 和 docker 已移除，开发环境请配置 E2B_API_KEY 使用 E2B 云服务。"
        )
