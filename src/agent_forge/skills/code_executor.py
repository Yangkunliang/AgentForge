"""内置代码执行 Skill — E2B 沙箱隔离执行

通过 SandboxManager + CubeSandboxE2BExecutor 在 KVM 级隔离沙箱中执行代码。

开发环境：E2B 云服务（配置 E2B_API_KEY 即可，无需本地 Docker/KVM）
生产环境：E2B 云服务 或 自部署 CubeSandbox（设置 CUBE_SANDBOX_URL 切换）

安全设计
--------
- 纵深防御：应用层黑名单检查 + E2B KVM 执行层隔离，两层独立
- 黑名单目的：尽早拒绝明显恶意代码，减少不必要的沙箱资源消耗
- 黑名单局限：无法覆盖所有绕过姿势，不作为唯一安全保障
- 执行层保障：KVM 独立内核，代码跑在完全隔离的 VM 里，无法逃逸宿主机

SSE 事件发射
------------
接受可选的 on_event 回调，由 SkillDispatcher 动态注入。
  sandbox_executing — 代码开始执行（含代码内容）
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
            template_id=sandbox_settings.cube_template_id,
        )
        _global_manager = SandboxManager(
            executor, ttl_seconds=sandbox_settings.cube_sandbox_timeout
        )
    return _global_manager


# ── 代码安全检查（纵深防御，不依赖沙箱隔离）────────────────────

# 高危模式匹配：尽早拒绝明显恶意代码，减少沙箱资源消耗
# 注意：黑名单不完备，不作为唯一安全保障，KVM 执行层是根本保障
_DANGEROUS_PATTERNS: list[str] = [
    "os.system",
    "os.popen",
    "subprocess",
    "__import__",
    "shutil",
    "eval(",
    'exec("__',   # 拦截 exec("__import__") 等攻击模式，不拦截合法的 exec(code, globals())
    'compile("__', # 拦截 compile("__...") 攻击，不拦截正则 compile(r"\d+", ...)
    "asyncio.create_subprocess",
    "pty",
    "ctypes",
    "cffi",
]


def _check_code_safety(code: str) -> str | None:
    """检查代码是否包含高危模式（纵深防御第一层）。

    Returns:
        None 表示通过；否则返回描述危险原因的字符串。
    """
    code_lower = code.lower()
    for pattern in _DANGEROUS_PATTERNS:
        if pattern.lower() in code_lower:
            return f"代码包含不安全的操作: `{pattern}`"
    return None


# ── 事件发射辅助 ────────────────────────────────────────────────

async def _emit(
    on_event: Callable[[str, dict], Awaitable[None]] | None,
    event_type: str,
    data: dict,
) -> None:
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
    """在 E2B 沙箱中执行 Python 代码。

    on_event 由 SkillDispatcher 动态注入。
    发射事件：sandbox_executing / sandbox_completed / sandbox_timeout
    """
    # 纵深防御第一层：应用层黑名单，尽早拒绝明显恶意代码
    safety_error = _check_code_safety(code)
    if safety_error:
        logger.warning("code_executor: blocked dangerous code: %s", safety_error)
        return {
            "success": False,
            "stdout": "",
            "stderr": f"[安全拦截] {safety_error}。",
            "exit_code": -1,
            "duration_ms": 0,
            "error": "blocked_unsafe_code",
        }

    manager = _get_manager()
    await _emit(on_event, "sandbox_executing", {"code": code})

    try:
        result = await manager.execute(code, timeout=timeout)

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

    except SandboxUnavailableError as e:
        logger.error("code_executor: sandbox unavailable: %s", e)
        return {
            "success": False,
            "stdout": "",
            "stderr": "代码执行服务暂时不可用，请检查 E2B_API_KEY 配置或稍后重试。",
            "exit_code": -1,
            "duration_ms": 0,
            "error": "sandbox_unavailable",
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
