"""内置代码执行 Skill — 沙箱隔离执行

通过 SandboxManager 在隔离环境中执行用户提交的 Python 代码。

Provider 路由
-------------
- 本地开发（macOS）：MockSandboxExecutor（无隔离）
- Linux CI：DockerSandboxExecutor（容器级隔离）
- 生产（LLM 生成代码）：CubeSandboxE2BExecutor（KVM 内核级隔离）

降级策略
--------
- CubeSandbox 不可用 → 降级到 DockerSandboxExecutor
- Docker 不可用 →
    - 开发模式（CUBE_SANDBOX_DEFAULT_PROVIDER=mock）：允许降级到 MockSandboxExecutor
    - 非开发模式：拒绝执行，返回错误（严禁在宿主机执行用户代码）

用法
----
    result = await code_executor(code="print('hello')")
    # {"success": True, "stdout": "hello\\n", "stderr": "", "exit_code": 0}
"""

from __future__ import annotations

import logging
from typing import Any

from agent_forge.config import sandbox_settings
from agent_forge.sandbox.base import (
    SandboxDestroyedError,
    SandboxTimeoutError,
    SandboxUnavailableError,
)
from agent_forge.sandbox.factory import SandboxProviderFactory
from agent_forge.sandbox.manager import SandboxManager

logger = logging.getLogger(__name__)

# ── OpenAI Tool 定义 ────────────────────────────────────────────

CODE_EXECUTOR_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "code_executor",
        "description": (
            "在隔离沙箱中执行 Python 代码并返回执行结果。"
            "当用户要求执行代码、运行脚本、验证算法、调试程序时调用此工具。"
            "不要凭猜测给出代码执行结果，必须调用此工具获取真实输出。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "要执行的 Python 代码",
                },
                "timeout": {
                    "type": "integer",
                    "description": "执行超时秒数，默认 30",
                    "default": 30,
                },
            },
            "required": ["code"],
        },
    },
}

# ── 懒加载 SandboxManager ────────────────────────────────────────

# 全局单例，避免每次调用重新创建 executor
_global_manager: SandboxManager | None = None


def _get_manager() -> SandboxManager:
    """懒加载 SandboxManager 单例"""
    global _global_manager
    if _global_manager is None:
        executor = SandboxProviderFactory.create(
            provider=sandbox_settings.cube_sandbox_default_provider,
            url=sandbox_settings.cube_sandbox_url,
            api_key=sandbox_settings.cube_sandbox_api_key,
            template_id=sandbox_settings.cube_template_id,
        )
        _global_manager = SandboxManager(
            executor, ttl_seconds=sandbox_settings.cube_sandbox_timeout
        )
    return _global_manager


def _is_dev_mode() -> bool:
    """当前是否为开发/测试模式（primary provider 配置为 mock）。

    mock provider 是唯一允许在宿主机执行代码的模式。
    任何其他 provider（docker / cubesandbox_*）均视为非开发模式，
    降级到 Mock 时直接拒绝，不允许在宿主机执行用户代码。
    """
    return sandbox_settings.cube_sandbox_default_provider == "mock"


# ── Skill 入口 ─────────────────────────────────────────────────

async def code_executor(
    code: str,
    timeout: int = 30,
) -> dict[str, Any]:
    """在沙箱中执行 Python 代码。

    降级策略：
    - CubeSandbox 不可用 → 降级到 DockerSandboxExecutor
    - Docker 不可用 → 仅开发模式允许降级到 MockSandboxExecutor；
      生产模式下直接返回错误，严禁在宿主机执行用户代码。
    """
    manager = _get_manager()

    try:
        result = await manager.execute(code, timeout=timeout)
        return {
            "success": True,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
            "duration_ms": result.duration_ms,
        }

    except SandboxUnavailableError as e:
        logger.warning(
            "code_executor: primary executor unavailable, "
            "attempting fallback: %s",
            e,
        )

        # ── 降级第一层：Docker（仅非 mock primary 时才有意义）──────────────
        if not _is_dev_mode():
            try:
                from agent_forge.sandbox.docker import DockerSandboxExecutor

                docker_executor = DockerSandboxExecutor()
                fallback_manager = SandboxManager(
                    docker_executor,
                    ttl_seconds=sandbox_settings.cube_sandbox_timeout,
                )
                result = await fallback_manager.execute(code, timeout=timeout)
                logger.warning("code_executor: degraded to DockerSandbox")
                return {
                    "success": True,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.exit_code,
                    "duration_ms": result.duration_ms,
                    "note": "degraded: cube_sandbox -> docker",
                }
            except Exception as fallback_e:
                # 生产环境 Docker 也失败 → 拒绝执行，安全优先
                logger.error(
                    "code_executor: docker fallback failed in non-dev mode, "
                    "refusing mock fallback for security: %s",
                    fallback_e,
                )
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": (
                        "代码执行服务暂时不可用（沙箱和 Docker 均无法连接），"
                        "请稍后重试。"
                    ),
                    "exit_code": -1,
                    "duration_ms": 0,
                    "error": "sandbox_unavailable",
                }

        # ── 降级第二层：Mock（仅开发模式，宿主机直接执行）─────────────────
        try:
            from agent_forge.sandbox.mock import MockSandboxExecutor

            mock_executor = MockSandboxExecutor()
            mock_manager = SandboxManager(
                mock_executor,
                ttl_seconds=sandbox_settings.cube_sandbox_timeout,
            )
            result = await mock_manager.execute(code, timeout=timeout)
            logger.warning(
                "code_executor: degraded to MockSandbox (dev mode, NO isolation)"
            )
            return {
                "success": True,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.exit_code,
                "duration_ms": result.duration_ms,
                "note": "degraded: mock (unsafe, dev only)",
            }
        except Exception as mock_e:
            logger.error("code_executor: mock fallback also failed: %s", mock_e)
            return {
                "success": False,
                "stdout": "",
                "stderr": str(mock_e),
                "exit_code": -1,
                "duration_ms": 0,
                "error": "sandbox_unavailable",
            }

    except SandboxTimeoutError as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1,
            "duration_ms": timeout * 1000,
            "error": "timeout",
        }

    except SandboxDestroyedError as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1,
            "duration_ms": 0,
            "error": "destroyed",
        }

    except Exception as e:
        logger.error("code_executor: unexpected error: %s", e)
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1,
            "duration_ms": 0,
            "error": "internal_error",
        }
