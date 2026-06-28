"""内置代码执行 Skill - E2B 沙箱隔离执行

通过 SandboxPool + CubeSandboxE2BExecutor 在 KVM 级隔离沙箱中执行代码。

并发控制
--------
- ``SandboxPool``：预置热沙箱池，降低冷启动延迟
- ``asyncio.Semaphore``：全局并发信号量，限制同时执行的沙箱数
- 优雅降级：信号量满或超时返回 ``sandbox_busy`` 错误

池生命周期管理
--------------
- ``init_sandbox_pool()``：应用启动时预热沙箱（调用 lifespan hook）
- ``shutdown_sandbox_pool()``：应用关闭时销毁池中所有沙箱

开发环境：E2B 云服务（配置 E2B_API_KEY 即可，无需本地 Docker/KVM）
生产环境：E2B 云服务 或 自部署 CubeSandbox（设置 CUBE_SANDBOX_URL 切换）

安全设计
--------
- 纵深防御：应用层黑名单检查 + E2B KVM 执行层隔离，两层独立
- 黑名单目的：尽早拒绝明显恶意代码，减少不必要的沙箱资源消耗
- 黑名单局限：无法覆盖所有绕过姿势，不作为唯一安全保障
- 执行层保障：KVM 独立内核，代码跑在完全隔离的 VM 里，无法逃逸宿主机

数据隔离
--------
- 每次 acquire -> execute -> release 之间执行 **cleanup**：杀掉子进程 + 清除 /tmp
- E2B 沙箱是 KVM 级隔离，内核级隔离由 E2B 保证
- 文件系统残留通过 cleanup 阶段解决

SSE 事件发射
------------
接受可选的 on_event 回调，由 SkillDispatcher 动态注入。
  sandbox_executing - 代码开始执行（含代码内容）
  sandbox_completed - 执行完成（含 exit_code 和耗时）
  sandbox_timeout   - 执行超时
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from agent_forge.config import sandbox_settings
from agent_forge.sandbox.base import (
    SandboxAcquireTimeoutError,
    SandboxDestroyedError,
    SandboxTimeoutError,
    SandboxUnavailableError,
)
from agent_forge.sandbox.factory import SandboxProviderFactory
from agent_forge.sandbox.pool import SandboxPool

logger = logging.getLogger(__name__)

# @dynamic-import SandboxConfig

# @dynamic-import SandboxConfig

# @dynamic-import SandboxConfig

# ── 全局池与信号量（懒加载）─────────────────────────────────────────

_global_pool: SandboxPool | None = None
_global_semaphore: asyncio.Semaphore | None = None


def _get_pool() -> SandboxPool:
    """懒加载 SandboxPool 单例。"""
    global _global_pool
    if _global_pool is None:
        executor = SandboxProviderFactory.create(
            provider=sandbox_settings.cube_sandbox_default_provider,
            url=sandbox_settings.cube_sandbox_url,
            template_id=sandbox_settings.cube_template_id,
        )
        from agent_forge.sandbox.base import SandboxConfig

        config = SandboxConfig(timeout_seconds=sandbox_settings.cube_sandbox_timeout)
        _global_pool = SandboxPool(
            executor=executor,
            config=config,
            min_size=sandbox_settings.sandbox_pool_min_size,
            max_size=sandbox_settings.sandbox_pool_max_size,
        )
    return _global_pool


def _get_semaphore() -> asyncio.Semaphore:
    """懒加载并发信号量单例。"""
    global _global_semaphore
    if _global_semaphore is None:
        _global_semaphore = asyncio.Semaphore(sandbox_settings.sandbox_max_concurrent)
    return _global_semaphore


# ── 池生命周期管理 ─────────────────────────────────────────────────

async def init_sandbox_pool() -> None:
    """应用启动时预热沙箱池。

    应在 FastAPI lifespan / startup hook 中调用。
    """
    pool = _get_pool()
    await pool.bootstrap()


async def shutdown_sandbox_pool() -> None:
    """应用关闭时销毁池中所有沙箱。

    应在 FastAPI lifespan / shutdown hook 中调用。
    """
    global _global_pool
    if _global_pool is not None:
        await _global_pool.drain()
        _global_pool = None
    global _global_semaphore
    _global_semaphore = None


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

    流程：黑名单检查 -> acquire semaphore -> pool acquire -> execute -> cleanup -> pool release -> release semaphore

    on_event 由 SkillDispatcher 动态注入。
    发射事件：sandbox_executing / sandbox_completed / sandbox_timeout
    """
    # 1. 纵深防御第一层：应用层黑名单，尽早拒绝明显恶意代码
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

    # 2. 获取全局依赖
    pool = _get_pool()
    semaphore = _get_semaphore()

    await _emit(on_event, "sandbox_executing", {"code": code})

    # 3. 获取信号量（并发控制 + 超时保护）
    semaphore_acquired = False
    try:
        semaphore_acquired = True
        await asyncio.wait_for(semaphore.acquire(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning("code_executor: semaphore wait timed out after %ds", timeout)
        return {
            "success": False,
            "stdout": "",
            "stderr": "代码执行服务繁忙，请稍后重试。",
            "exit_code": -1,
            "duration_ms": 0,
            "error": "sandbox_busy",
        }

    pool_info = None
    pool_acquired = False
    try:
        # 4. 从池中获取沙箱（支持超时，池空时冷启动）
        pool_info = await pool.acquire(timeout=sandbox_settings.sandbox_acquire_timeout)
        pool_acquired = True

        # 5. 执行代码
        result = await pool._executor.execute(
            pool_info.sandbox_id, code, timeout=timeout
        )

        # 6. 清理沙箱状态（为复用做准备）
        await pool.cleanup(pool_info.sandbox_id)

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
        logger.warning("code_executor: sandbox was destroyed: %s", e)
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1,
            "duration_ms": 0,
            "error": "destroyed",
        }

    except SandboxAcquireTimeoutError as e:
        logger.warning("code_executor: acquire timeout: %s", e)
        return {
            "success": False,
            "stdout": "",
            "stderr": "获取沙箱超时，请稍后重试。",
            "exit_code": -1,
            "duration_ms": 0,
            "error": "sandbox_busy",
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

    finally:
        # 7. 释放信号量（保证任何路径都释放）
        if semaphore_acquired:
            semaphore.release()

        # 8. 沙箱泄漏防护：如果 acquire 成功但 try 体中途异常退出，
        #    pool_info 非 None 且 pool_acquired 为 True，说明沙箱已取走
        #    但 cleanup/release 未走到。此时应尝试 cleanup 后再归还，
        #    避免沙箱永远留在池外消耗 E2B 配额。
        if pool_acquired and pool_info is not None:
            try:
                await pool.cleanup(pool_info.sandbox_id)
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "code_executor: leak-path cleanup failed for %s: %s",
                    pool_info.sandbox_id, e,
                )
            try:
                await pool.release(pool_info)
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "code_executor: leak-path release failed for %s: %s",
                    pool_info.sandbox_id, e,
                )
