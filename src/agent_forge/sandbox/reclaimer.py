"""
agent_forge.sandbox.reclaimer
===============================
TTL 自动回收器：后台协程扫描沙箱生命周期，对超时沙箱执行 pause → destroy。

工作模式
--------
- 每 N 秒（可配置，默认 60s）扫描一次
- 对已 pause 且超过 pause_ttl 的沙箱执行 destroy
- 通过 SandboxPool.drain() 销毁池中所有沙箱

集成方式
--------
在 ``src/api/main.py`` 的 lifespan 中启动/关闭：

    async with SandboxReclaimer() as reclaimer:
        yield
"""

from __future__ import annotations

import asyncio
import logging
import time

from agent_forge.config import sandbox_settings
from agent_forge.sandbox.base import SandboxState
from agent_forge.sandbox.factory import SandboxProviderFactory
from agent_forge.sandbox.manager import SandboxManager
from agent_forge.sandbox.pool import SandboxPool

logger = logging.getLogger(__name__)


class SandboxReclaimer:
    """TTL 自动回收后台协程。

    职责：
    1. 定期扫描 SandboxPool 中沙箱的超时状态
    2. 对已超时但未 pause 的沙箱执行 pause
    3. 对已 pause 且超过 pause_ttl 的沙箱执行 destroy
    4. 应用关闭时通过 drain() 销毁全部沙箱
    """

    def __init__(
        self,
        *,
        interval: int = 60,
        pause_ttl: int = 120,
    ) -> None:
        """
        Args:
            interval:   扫描间隔（秒）
            pause_ttl:  pause 后存活多久再 destroy
        """
        self._interval = interval
        self._pause_ttl = pause_ttl
        self._running = False
        self._task: asyncio.Task | None = None

        # 懒初始化 Pool 和 Executor
        self._executor = None
        self._pool: SandboxPool | None = None

    async def _ensure_initialized(self) -> None:
        """懒初始化 executor 和 pool。"""
        if self._executor is not None:
            return
        self._executor = SandboxProviderFactory.create(
            provider=sandbox_settings.cube_sandbox_default_provider,
            url=sandbox_settings.cube_sandbox_url,
            api_key=sandbox_settings.cube_sandbox_api_key,
            template_id=sandbox_settings.cube_template_id,
        )
        self._pool = SandboxPool(
            executor=self._executor,
            config=None,  # pool 不持 config，由 acquire 按需创建
            min_size=0,  # reclaimer 不预热，按需冷启动
            max_size=10,
        )
        logger.info("SandboxReclaimer: initialized (interval=%ds, pause_ttl=%ds)",
                     self._interval, self._pause_ttl)

    async def _scan_and_reclaim(self) -> None:
        """单次扫描：检查池中沙箱状态，执行 pause/destroy。"""
        if self._pool is None:
            return

        # 获取池中所有 ConnectInfo 并检查超时
        temp_items: list = []
        while not self._pool._pool.empty():
            try:
                temp_items.append(self._pool._pool.get_nowait())
            except asyncio.QueueEmpty:
                break

        reclaimed = 0
        for info in temp_items:
            if info.is_expired:
                logger.info(
                    "SandboxReclaimer: sandbox_id=%s expired, destroying",
                    info.sandbox_id,
                )
                try:
                    await self._executor.destroy(info.sandbox_id)
                    reclaimed += 1
                except Exception as e:
                    logger.warning("SandboxReclaimer: destroy failed: %s", e)
            else:
                # 未过期，放回池中
                try:
                    self._pool._pool.put_nowait(info)
                except asyncio.QueueFull:
                    # 池满时销毁
                    await self._executor.destroy(info.sandbox_id)
                    reclaimed += 1

        logger.debug("SandboxReclaimer: scan complete, reclaimed=%d", reclaimed)

    async def _loop(self) -> None:
        """后台扫描循环。"""
        logger.info("SandboxReclaimer: started (interval=%ds)", self._interval)
        while self._running:
            await self._ensure_initialized()
            await self._scan_and_reclaim()
            await asyncio.sleep(self._interval)
        logger.info("SandboxReclaimer: stopped")

    async def start(self) -> None:
        """启动后台扫描协程。"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("SandboxReclaimer: task created")

    async def stop(self) -> None:
        """停止后台协程，并 drain 池中所有沙箱。"""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        # 销毁池中所有沙箱
        if self._pool is not None:
            await self._pool.drain()
            logger.info("SandboxReclaimer: pool drained")

    async def __aenter__(self) -> "SandboxReclaimer":
        await self.start()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.stop()
