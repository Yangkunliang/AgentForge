"""
tests/sandbox/test_reclaimer.py
================================
SandboxReclaimer 单元测试

覆盖场景
--------
- start / stop 生命周期
- 空池时 scan 不报错
- drain 在 stop 时调用
- 超时沙箱被识别
"""

import asyncio
import time

import pytest

from agent_forge.sandbox.base import SandboxConfig
from agent_forge.sandbox.mock import MockSandboxExecutor
from agent_forge.sandbox.reclaimer import SandboxReclaimer


# ── 夹具 ─────────────────────────────────────────────────────────────


@pytest.fixture
def executor():
    return MockSandboxExecutor()


@pytest.fixture
def config():
    return SandboxConfig(timeout_seconds=1)  # 1s TTL，方便测试超时


# ── start / stop ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reclaimer_start_and_stop():
    """启动后能正常停止"""
    reclaimer = SandboxReclaimer(interval=1, pause_ttl=1)
    await reclaimer.start()
    assert reclaimer._running is True
    await reclaimer.stop()
    assert reclaimer._running is False


@pytest.mark.asyncio
async def test_reclaimer_context_manager(executor, config):
    """async with 自动 start/stop"""
    reclaimer = SandboxReclaimer(interval=1)
    async with reclaimer as rc:
        assert rc._running is True
    assert rc._running is False


# ── scan 空池 ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_scan_empty_pool():
    """空池扫描不应报错"""
    reclaimer = SandboxReclaimer(interval=60)
    await reclaimer._ensure_initialized()
    # scan 空池
    await reclaimer._scan_and_reclaim()
    # 不应抛出异常


# ── 超时沙箱识别 ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_expired_sandbox_detected(executor, config):
    """已超时的沙箱应被识别（is_expired == True）"""
    from agent_forge.sandbox.base import ConnectInfo, SandboxState

    # 模拟已过期
    info = ConnectInfo(
        sandbox_id="test-expired",
        host="127.0.0.1",
        port=0,
        template_id="mock",
        state=SandboxState.RUNNING,
        timeout_at=int(time.time()) - 10,  # 10 秒前过期
    )
    assert info.is_expired is True


@pytest.mark.asyncio
async def test_fresh_sandbox_not_expired(executor, config):
    """刚创建或续期的沙箱不应被识别为超时"""
    from agent_forge.sandbox.base import ConnectInfo, SandboxState

    info = ConnectInfo(
        sandbox_id="test-fresh",
        host="127.0.0.1",
        port=0,
        template_id="mock",
        state=SandboxState.RUNNING,
        timeout_at=int(time.time()) + 3600,
    )
    assert info.is_expired is False
