"""
tests/sandbox/test_manager.py
================================
SandboxManager 单元测试

覆盖场景
--------
- 首次调用 get_or_create 创建沙箱
- 重复调用续期（TTL 未过期）
- TTL 超时后重建沙箱
- destroy 后抛出 SandboxDestroyedError
- execute / execute_shell / files_read / files_write 快捷方法
- 上下文管理器（async with）自动销毁
"""

import asyncio
import time

import pytest

from agent_forge.sandbox.base import SandboxConfig, SandboxDestroyedError
from agent_forge.sandbox.manager import SandboxManager
from tests.sandbox.fakes import InMemorySandboxExecutor, _TEST_SANDBOX_REGISTRY


# ── 夹具 ─────────────────────────────────────────────────────────────

@pytest.fixture
def executor():
    return InMemorySandboxExecutor()


@pytest.fixture
def manager(executor):
    return SandboxManager(executor, ttl_seconds=300)


# ── get_or_create ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_first_get_or_create_creates_sandbox(manager):
    assert manager.sandbox_id is None
    sid = await manager.get_or_create()
    assert sid is not None
    assert manager.sandbox_id == sid
    await manager.destroy()


@pytest.mark.asyncio
async def test_get_or_create_returns_same_id_within_ttl(manager):
    sid1 = await manager.get_or_create()
    sid2 = await manager.get_or_create()
    assert sid1 == sid2
    await manager.destroy()


@pytest.mark.asyncio
async def test_get_or_create_rebuilds_on_ttl_expiry(executor):
    """TTL 设为极短（1s），等待超时后应重建沙箱"""
    manager = SandboxManager(executor, ttl_seconds=1)
    sid1 = await manager.get_or_create()

    # 强制 _last_access 提前，使 elapsed > ttl
    manager._last_access = time.monotonic() - 2

    sid2 = await manager.get_or_create()
    assert sid2 != sid1  # 沙箱已重建
    await manager.destroy()


# ── destroy ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_destroy_marks_manager_as_destroyed(manager):
    await manager.get_or_create()
    await manager.destroy()
    assert manager.is_destroyed


@pytest.mark.asyncio
async def test_get_or_create_after_destroy_raises(manager):
    await manager.get_or_create()
    await manager.destroy()
    with pytest.raises(SandboxDestroyedError):
        await manager.get_or_create()


@pytest.mark.asyncio
async def test_destroy_is_idempotent(manager):
    await manager.get_or_create()
    await manager.destroy()
    await manager.destroy()  # 不应抛出异常


# ── execute / execute_shell ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_execute_creates_sandbox_and_runs_code(manager):
    result = await manager.execute("print('mgr test')")
    assert "mgr test" in result.stdout
    assert result.exit_code == 0
    await manager.destroy()


@pytest.mark.asyncio
async def test_execute_shell_runs_command(manager):
    result = await manager.execute_shell("echo shell_ok")
    assert "shell_ok" in result.stdout
    await manager.destroy()


# ── files_read / files_write ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_files_write_and_read_via_manager(manager):
    await manager.files_write("/tmp/mgr.txt", "manager content")
    content = await manager.files_read("/tmp/mgr.txt")
    assert content == "manager content"
    await manager.destroy()


# ── 上下文管理器 ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_context_manager_destroys_on_exit(executor):
    async with SandboxManager(executor, ttl_seconds=60) as mgr:
        await mgr.execute("pass")
        sid = mgr.sandbox_id

    assert mgr.is_destroyed
    # 沙箱应已被销毁
    assert sid not in _TEST_SANDBOX_REGISTRY


# ── 属性 ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sandbox_id_is_none_before_create(manager):
    assert manager.sandbox_id is None


@pytest.mark.asyncio
async def test_sandbox_id_is_none_after_destroy(manager):
    await manager.get_or_create()
    await manager.destroy()
    assert manager.sandbox_id is None
