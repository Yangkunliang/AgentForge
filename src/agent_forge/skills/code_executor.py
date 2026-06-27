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

SSE 事件发射（TASK-009）
------------------------
接受可选的 on_event 回调，由 SkillDispatcher 动态注入。
在关键执行节点发射事件供前端可视化：
  sandbox_executing — 代码开始执行（含代码内容，供前端展示代码块）
  sandbox_completed — 执行完成（含 exit_code 和耗时）
  sandbox_timeout   — 执行超时
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
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

_global_manager: SandboxManager | None = None


def _get_manager() -> SandboxManager:
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
    """当前是否为开发模式（primary provider 配置为 mock）。"""
    return sandbox_settings.cube_sandbox_default_provider == "mock"


# ── 事件发射辅助 ────────────────────────────────────────────────

async def _emit(
    on_event: Callable[[str, dict], Awaitable[None]] | None,
    event_type: str,
    data: dict,
) -> None:
    """安全地发射 SSE 事件，忽略回调不存在或回调异常的情况。"""
    if on_event is None:
        return
    try:
        await on_event(event_type, data)
    except Exception as e:
        logger.warning("code_executor: on_event callback error (%s): %s", event_type, e)


# ── Skill 入口 ─────────────────────────────────────────────────

async def code_executor(
    code: str,
    timeout: int = 30,
    on_event: Callable[[str, dict], Awaitable[None]] | None = None,
) -> dict[str, Any]:
    """在沙箱中执行 Python 代码。

    on_event 由 SkillDispatcher 动态注入（检测到函数签名含 on_event 参数时注入）。
    在关键节点发射事件：
      sandbox_executing  — 执行前，携带完整代码供前端展示代码块
      sandbox_completed  — 执行成功，携带 exit_code 和 duration_ms
      sandbox_timeout    — 执行超时

    降级策略：
      非开发模式：CubeSandbox → Docker → 拒绝执行（不允许在宿主机执行用户代码）
      开发模式：   CubeSandbox → Docker → MockSandbox
    """
    manager = _get_manager()

    # 执行前发射事件：前端用此展示代码块 + loading 动画
    await _emit(on_event, "sandbox_executing", {"code": code})

    try:
        result = await manager.execute(code, timeout=timeout)

        # 执行成功：发射完成事件（结果由 tool_call_end 携带，这里只推耗时）
        await _emit(on_event, "sandbox_completed", {
            "exit_code": result.exit_code,
            "duration_ms": result.duration_ms,
        })

        return {
            "success": True,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
            "duration_ms": result.duration_ms,
        }

    except SandboxUnavailableError as e:
        logger.warning("code_executor: primary unavailable, attempting fallback: %s", e)

        # ── 降级第一层：Docker（非 dev 模式才有意义）──────────────
        if not _is_dev_mode():
            try:
                from agent_forge.sandbox.docker import DockerSandboxExecutor

                fallback_manager = SandboxManager(
                    DockerSandboxExecutor(),
                    ttl_seconds=sandbox_settings.cube_sandbox_timeout,
                )
                result = await fallback_manager.execute(code, timeout=timeout)
                logger.warning("code_executor: degraded to DockerSandbox")

                await _emit(on_event, "sandbox_completed", {
                    "exit_code": result.exit_code,
                    "duration_ms": result.duration_ms,
                    "note": "degraded:docker",
                })

                return {
                    "success": True,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.exit_code,
                    "duration_ms": result.duration_ms,
                    "note": "degraded: cube_sandbox -> docker",
                }
            except Exception as fallback_e:
                # 生产环境 Docker 也失败 → 拒绝执行
                logger.error(
                    "code_executor: docker fallback failed in non-dev mode, "
                    "refusing mock for security: %s",
                    fallback_e,
                )
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": "代码执行服务暂时不可用（沙箱和 Docker 均无法连接），请稍后重试。",
                    "exit_code": -1,
                    "duration_ms": 0,
                    "error": "sandbox_unavailable",
                }

        # ── 降级第二层：Mock（仅开发模式）────────────────────────
        try:
            from agent_forge.sandbox.mock import MockSandboxExecutor

            mock_manager = SandboxManager(
                MockSandboxExecutor(),
                ttl_seconds=sandbox_settings.cube_sandbox_timeout,
            )
            result = await mock_manager.execute(code, timeout=timeout)
            logger.warning("code_executor: degraded to MockSandbox (dev, NO isolation)")

            await _emit(on_event, "sandbox_completed", {
                "exit_code": result.exit_code,
                "duration_ms": result.duration_ms,
                "note": "degraded:mock",
            })

            return {
                "success": True,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.exit_code,
                "duration_ms": result.duration_ms,
                "note": "degraded: mock (unsafe, dev only)",
            }
        except Exception as mock_e:
            logger.error("code_executor: mock fallback failed: %s", mock_e)
            return {
                "success": False,
                "stdout": "",
                "stderr": str(mock_e),
                "exit_code": -1,
                "duration_ms": 0,
                "error": "sandbox_unavailable",
            }

    except SandboxTimeoutError as e:
        await _emit(on_event, "sandbox_timeout", {"timeout_seconds": timeout})
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
