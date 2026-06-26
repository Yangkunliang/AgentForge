"""
tests/sandbox/test_pool.py
============================
SandboxPool 单元测试

覆盖场景
--------
- bootstrap 预热：创建 min_size 个沙箱
- acquire：命中池（热取）
- acquire：冷启动（池空）
- release：归还到池
- release：池满时销毁
- drain：清空并销毁池中所有沙箱
- size 属性
"""

import pytest

from agent_forge.sandbox.base import SandboxConfig
from agent_forge.sandbox.mock import MockSandboxExecutor, _MOCK_REGISTRY
from agent_forge.sandbox.pool import SandboxPool


# ── 夹具 ─────────────────────────────────────────────────────────────

@pytest.fixture
def executor():
    return MockSandboxExecutor()


@pytest.fixture
def config():
    return SandboxConfig(timeout_seconds=60)


# ── bootstrap ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bootstrap_creates_min_size_sandboxes(executor, config):
    pool = SandboxPool(executor=executor, config=config, min_size=3, max_size=10)
    await pool.bootstrap()
    assert pool.size == 3
    await pool.drain()


@pytest.mark.asyncio
async def test_bootstrap_zero_creates_nothing(executor, config):
    pool = SandboxPool(executor=executor, config=config, min_size=0, max_size=10)
    await pool.bootstrap()
    assert pool.size == 0


# ── acquire ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_acquire_from_warmed_pool(executor, config):
    pool = SandboxPool(executor=executor, config=config, min_size=2, max_size=10)
    await pool.bootstrap()
    size_before = pool.size

    info = await pool.acquire()
    assert info.sandbox_id is not None
    assert pool.size == size_before - 1

    await pool.drain()
    await executor.destroy(info.sandbox_id)


@pytest.mark.asyncio
async def test_acquire_cold_start_when_pool_empty(executor, config):
    """池为空时应冷启动新沙箱"""
    pool = SandboxPool(executor=executor, config=config, min_size=0, max_size=10)
    info = await pool.acquire()
    assert info.sandbox_id is not None
    assert info.sandbox_id in _MOCK_REGISTRY
    await executor.destroy(info.sandbox_id)


# ── release ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_release_returns_sandbox_to_pool(executor, config):
    pool = SandboxPool(executor=executor, config=config, min_size=0, max_size=5)
    info = await pool.acquire()
    await pool.release(info)
    assert pool.size == 1
    await pool.drain()


@pytest.mark.asyncio
async def test_release_destroys_sandbox_when_pool_full(executor, config):
    pool = SandboxPool(executor=executor, config=config, min_size=0, max_size=1)
    info1 = await pool.acquire()
    info2 = await pool.acquire()

    # 放入第一个：池满
    await pool.release(info1)
    assert pool.size == 1

    # 放入第二个：池满，应销毁 info2
    await pool.release(info2)
    assert pool.size == 1  # 池大小不变
    assert info2.sandbox_id not in _MOCK_REGISTRY  # info2 已被销毁

    await pool.drain()


# ── drain ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_drain_empties_pool_and_destroys_sandboxes(executor, config):
    pool = SandboxPool(executor=executor, config=config, min_size=3, max_size=10)
    await pool.bootstrap()

    # 记录池中所有 sandbox_id
    pool_ids = []
    while pool.size > 0:
        info = await pool.acquire()
        pool_ids.append(info.sandbox_id)

    assert pool.size == 0

    # drain 空池
    await pool.drain()
    assert pool.size == 0

    # 已 acquire 的沙箱应仍在注册表中（drain 只销毁池内沙箱）
    for sid in pool_ids:
        assert sid in _MOCK_REGISTRY

    # 手动销毁已 acquire 的沙箱
    for sid in pool_ids:
        await executor.destroy(sid)


@pytest.mark.asyncio
async def test_drain_is_safe_on_empty_pool(executor, config):
    pool = SandboxPool(executor=executor, config=config, min_size=0, max_size=10)
    # drain 空池不应抛出异常
    await pool.drain()
    assert pool.size == 0


# ── size 属性 ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_size_reflects_pool_contents(executor, config):
    pool = SandboxPool(executor=executor, config=config, min_size=0, max_size=10)
    assert pool.size == 0

    info = await pool.acquire()
    await pool.release(info)
    assert pool.size == 1

    info2 = await pool.acquire()
    assert pool.size == 0

    await executor.destroy(info2.sandbox_id)
