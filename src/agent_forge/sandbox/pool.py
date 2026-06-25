"""
agent_forge.sandbox.pool
=========================
SandboxPool：预置热沙箱池，降低冷启动延迟。

适用场景
--------
- 高并发场景下，每次按需创建沙箱的 ~60ms 冷启动不可接受
- 需要 CubeSandbox 集群支持（单机资源不够维持大型热池）

用法示例
--------
    from agent_forge.sandbox.pool import SandboxPool
    from agent_forge.sandbox.cubesandbox import CubeSandboxAPIExecutor
    from agent_forge.sandbox.base import SandboxConfig

    executor = CubeSandboxAPIExecutor(base_url="...", api_key="...")
    config   = SandboxConfig(template_id="tpl-python", timeout_seconds=300)
    pool     = SandboxPool(executor=executor, config=config, min_size=5, max_size=50)

    # 应用启动时预热
    await pool.bootstrap()

    # 请求时使用
    info = await pool.acquire()
    try:
        result = await executor.execute(info.sandbox_id, "print('hi')")
    finally:
        await pool.release(info)   # 归还或销毁
"""

from __future__ import annotations

import asyncio
import logging

from agent_forge.sandbox.base import ConnectInfo, SandboxConfig, SandboxExecutor

logger = logging.getLogger(__name__)


class SandboxPool:
    """预置热沙箱池。

    维护一个 asyncio.Queue，提前创建好若干沙箱（热沙箱），
    请求到来时直接从池中取用，避免冷启动延迟。

    线程安全：asyncio.Queue 本身是协程安全的，但不跨线程。

    Args:
        executor:   沙箱执行器实例
        config:     创建沙箱时使用的配置（含 template_id、ttl 等）
        min_size:   预热沙箱数量（bootstrap() 时创建）
        max_size:   池的最大容量；超出后归还的沙箱直接销毁
    """

    def __init__(
        self,
        executor: SandboxExecutor,
        config: SandboxConfig,
        min_size: int = 5,
        max_size: int = 50,
    ) -> None:
        self._executor = executor
        self._config = config
        self._pool: asyncio.Queue[ConnectInfo] = asyncio.Queue(maxsize=max_size)
        self._min_size = min_size

    async def bootstrap(self) -> None:
        """预热：预创建 min_size 个沙箱，应在应用启动时调用一次。

        若预热失败（如 CubeSandbox 服务未就绪），记录警告后继续，
        后续请求会走冷启动路径。
        """
        created = 0
        for _ in range(self._min_size):
            try:
                info = await self._executor.create(self._config)
                await self._pool.put(info)
                created += 1
            except Exception as e:  # noqa: BLE001
                logger.warning("SandboxPool: bootstrap 预热失败（已创建 %d/%d）: %s",
                               created, self._min_size, e)
                break
        logger.info("SandboxPool: 预热完成，热沙箱数量 %d/%d", created, self._min_size)

    async def acquire(self) -> ConnectInfo:
        """从池中获取一个沙箱。

        如果池为空，冷启动新沙箱（等待 ~60ms）。
        """
        try:
            info = self._pool.get_nowait()
            logger.debug("SandboxPool: acquired sandbox_id=%s from pool", info.sandbox_id)
            return info
        except asyncio.QueueEmpty:
            logger.debug("SandboxPool: pool empty, cold-starting new sandbox")
            return await self._executor.create(self._config)

    async def release(self, info: ConnectInfo) -> None:
        """归还沙箱到池中；池满时直接销毁。"""
        try:
            self._pool.put_nowait(info)
            logger.debug("SandboxPool: released sandbox_id=%s back to pool", info.sandbox_id)
        except asyncio.QueueFull:
            logger.debug("SandboxPool: pool full, destroying sandbox_id=%s", info.sandbox_id)
            await self._executor.destroy(info.sandbox_id)

    async def drain(self) -> None:
        """销毁池中所有沙箱，应在应用关闭时调用。"""
        destroyed = 0
        while not self._pool.empty():
            try:
                info = self._pool.get_nowait()
                await self._executor.destroy(info.sandbox_id)
                destroyed += 1
            except asyncio.QueueEmpty:
                break
            except Exception as e:  # noqa: BLE001
                logger.warning("SandboxPool: drain 时销毁沙箱失败: %s", e)
        logger.info("SandboxPool: drain 完成，已销毁 %d 个沙箱", destroyed)

    @property
    def size(self) -> int:
        """当前池中可用沙箱数量。"""
        return self._pool.qsize()
