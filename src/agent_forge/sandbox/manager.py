"""
agent_forge.sandbox.manager
============================
SandboxManager：沙箱生命周期管理器。

职责
----
- 维护单个 sandbox_id 的生命周期（创建、TTL 续期、超时销毁）
- executor 在构造时注入，manager 本身不创建 executor 实例
- 提供 execute() 快捷方法，自动处理沙箱的创建与续期

用法示例
--------
    from agent_forge.sandbox import SandboxManager
    from agent_forge.sandbox.cubesandbox import CubeSandboxAPIExecutor

    executor = CubeSandboxAPIExecutor(base_url="http://...", api_key="...")
    manager  = SandboxManager(executor, ttl_seconds=300)

    result = await manager.execute("print('hello')")
    print(result.stdout)   # hello

    await manager.destroy()
"""

from __future__ import annotations

import logging
import time

from agent_forge.sandbox.base import (
    ExecResult,
    SandboxConfig,
    SandboxDestroyedError,
    SandboxExecutor,
)

logger = logging.getLogger(__name__)


class SandboxManager:
    """沙箱生命周期管理器。

    管理单个沙箱实例的 sandbox_id，负责：
    - 首次调用时按需创建沙箱
    - 每次访问时检查 TTL，超时则重建
    - 未超时时调用 connect() 续期 TTL 计时器
    - 提供 execute() / execute_shell() 快捷方法

    注意：不持有 SandboxFactory，executor 由调用方构造后注入，
    保证 self._executor 永远不为 None。
    """

    def __init__(self, executor: SandboxExecutor, ttl_seconds: int = 300) -> None:
        """
        Args:
            executor:     已构造好的沙箱执行器实例（Mock / Docker / CubeSandbox）
            ttl_seconds:  沙箱最大空闲时间（秒），超时后重建沙箱
        """
        self._executor: SandboxExecutor = executor
        self._ttl: int = ttl_seconds
        self._sandbox_id: str | None = None
        self._last_access: float = 0.0
        self._destroyed: bool = False

    # ── 生命周期核心 ──────────────────────────────────────────────────────────

    async def get_or_create(self) -> str:
        """返回当前可用的 sandbox_id，必要时创建新沙箱或续期。

        Returns:
            sandbox_id: 可以立即使用的沙箱 ID

        Raises:
            SandboxDestroyedError: manager 已被显式销毁
        """
        if self._destroyed:
            raise SandboxDestroyedError(
                "SandboxManager 已销毁，请重新创建实例"
            )

        now = time.monotonic()

        if self._sandbox_id is None:
            # 首次使用：创建新沙箱
            logger.debug("sandbox: creating new sandbox (ttl=%ds)", self._ttl)
            config = SandboxConfig(timeout_seconds=self._ttl)
            info = await self._executor.create(config)
            self._sandbox_id = info.sandbox_id
            self._last_access = now
            logger.info("sandbox: created sandbox_id=%s", self._sandbox_id)

        else:
            elapsed = now - self._last_access
            if elapsed > self._ttl:
                # TTL 超时：销毁旧沙箱，重建
                logger.info(
                    "sandbox: TTL expired (elapsed=%.1fs), rebuilding sandbox_id=%s",
                    elapsed, self._sandbox_id,
                )
                await self._executor.destroy(self._sandbox_id)
                config = SandboxConfig(timeout_seconds=self._ttl)
                info = await self._executor.create(config)
                self._sandbox_id = info.sandbox_id
                logger.info("sandbox: rebuilt sandbox_id=%s", self._sandbox_id)
            else:
                # 未超时：续期（重置 CubeSandbox / Docker 的 TTL 计时器）
                await self._executor.connect(self._sandbox_id, timeout=0)
                logger.debug(
                    "sandbox: renewed sandbox_id=%s (elapsed=%.1fs)",
                    self._sandbox_id, elapsed,
                )
            self._last_access = now

        return self._sandbox_id

    async def destroy(self) -> None:
        """彻底销毁当前沙箱并将 manager 标记为不可用。幂等。"""
        if not self._destroyed and self._sandbox_id:
            logger.info("sandbox: destroying sandbox_id=%s", self._sandbox_id)
            await self._executor.destroy(self._sandbox_id)
        self._sandbox_id = None
        self._destroyed = True

    # ── 快捷执行方法 ─────────────────────────────────────────────────────────

    async def execute(self, code: str, timeout: int = 30) -> ExecResult:
        """在当前沙箱中执行 Python 代码（自动处理沙箱生命周期）。

        Args:
            code:    要执行的 Python 代码字符串
            timeout: 执行超时秒数
        """
        sandbox_id = await self.get_or_create()
        return await self._executor.execute(sandbox_id, code, timeout=timeout)

    async def execute_shell(self, command: str, timeout: int = 30) -> ExecResult:
        """在当前沙箱中执行 Shell 命令（自动处理沙箱生命周期）。

        Args:
            command: Shell 命令字符串
            timeout: 执行超时秒数
        """
        sandbox_id = await self.get_or_create()
        return await self._executor.execute_shell(sandbox_id, command, timeout=timeout)

    async def files_write(self, path: str, content: str) -> None:
        """向沙箱内写入文件。"""
        sandbox_id = await self.get_or_create()
        await self._executor.files_write(sandbox_id, path, content)

    async def files_read(self, path: str) -> str:
        """读取沙箱内文件内容。"""
        sandbox_id = await self.get_or_create()
        return await self._executor.files_read(sandbox_id, path)

    # ── 上下文管理器支持 ─────────────────────────────────────────────────────

    async def __aenter__(self) -> "SandboxManager":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.destroy()

    # ── 状态查询 ─────────────────────────────────────────────────────────────

    @property
    def sandbox_id(self) -> str | None:
        """当前沙箱 ID，未创建或已销毁时为 None。"""
        return self._sandbox_id

    @property
    def is_destroyed(self) -> bool:
        return self._destroyed
