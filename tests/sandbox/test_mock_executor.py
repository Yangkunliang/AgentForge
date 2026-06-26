"""
tests/sandbox/test_mock_executor.py
=====================================
MockSandboxExecutor 单元测试

覆盖场景
--------
- create / execute / destroy 基础生命周期
- execute_shell
- files_read / files_write
- TTL 超时（通过 ConnectInfo.is_expired 验证）
- 路径隔离（沙箱 A 无法读取沙箱 B 的文件）
- pause 后操作抛出 SandboxDestroyedError
- destroy 幂等性
"""

import asyncio
import time

import pytest

from agent_forge.sandbox.base import (
    SandboxConfig,
    SandboxDestroyedError,
    SandboxTimeoutError,
    SandboxState,
)
from agent_forge.sandbox.mock import MockSandboxExecutor, _MOCK_REGISTRY


# ── 测试夹具 ──────────────────────────────────────────────────────────

@pytest.fixture
def executor():
    return MockSandboxExecutor()


@pytest.fixture
def config():
    return SandboxConfig(timeout_seconds=60)


# ── create ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_returns_connect_info(executor, config):
    info = await executor.create(config)
    assert info.sandbox_id.startswith("mock-")
    assert info.host == "127.0.0.1"
    assert info.port == 0
    assert info.sandbox_id in _MOCK_REGISTRY


@pytest.mark.asyncio
async def test_create_multiple_sandboxes_are_independent(executor, config):
    info1 = await executor.create(config)
    info2 = await executor.create(config)
    assert info1.sandbox_id != info2.sandbox_id
    assert info1.sandbox_id in _MOCK_REGISTRY
    assert info2.sandbox_id in _MOCK_REGISTRY
    # cleanup
    await executor.destroy(info1.sandbox_id)
    await executor.destroy(info2.sandbox_id)


# ── execute ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_execute_python_code(executor, config):
    info = await executor.create(config)
    result = await executor.execute(info.sandbox_id, "print('hello')")
    assert result.stdout.strip() == "hello"
    assert result.exit_code == 0
    assert result.duration_ms >= 0
    await executor.destroy(info.sandbox_id)


@pytest.mark.asyncio
async def test_execute_captures_stderr(executor, config):
    info = await executor.create(config)
    result = await executor.execute(
        info.sandbox_id,
        "import sys; sys.stderr.write('err\\n')"
    )
    assert "err" in result.stderr
    await executor.destroy(info.sandbox_id)


@pytest.mark.asyncio
async def test_execute_nonzero_exit_code(executor, config):
    info = await executor.create(config)
    result = await executor.execute(info.sandbox_id, "raise SystemExit(1)")
    assert result.exit_code != 0
    await executor.destroy(info.sandbox_id)


@pytest.mark.asyncio
async def test_execute_timeout(executor, config):
    info = await executor.create(config)
    with pytest.raises(SandboxTimeoutError):
        await executor.execute(info.sandbox_id, "import time; time.sleep(10)", timeout=1)
    await executor.destroy(info.sandbox_id)


@pytest.mark.asyncio
async def test_execute_on_destroyed_sandbox(executor, config):
    info = await executor.create(config)
    await executor.destroy(info.sandbox_id)
    with pytest.raises(SandboxDestroyedError):
        await executor.execute(info.sandbox_id, "print('hi')")


# ── execute_shell ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_execute_shell(executor, config):
    info = await executor.create(config)
    result = await executor.execute_shell(info.sandbox_id, "echo hello_shell")
    assert "hello_shell" in result.stdout
    assert result.exit_code == 0
    await executor.destroy(info.sandbox_id)


# ── files_read / files_write ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_files_write_and_read(executor, config):
    info = await executor.create(config)
    await executor.files_write(info.sandbox_id, "/tmp/test.txt", "hello file")
    content = await executor.files_read(info.sandbox_id, "/tmp/test.txt")
    assert content == "hello file"
    await executor.destroy(info.sandbox_id)


@pytest.mark.asyncio
async def test_files_read_nonexistent_raises(executor, config):
    info = await executor.create(config)
    with pytest.raises(FileNotFoundError):
        await executor.files_read(info.sandbox_id, "/not/exist.txt")
    await executor.destroy(info.sandbox_id)


@pytest.mark.asyncio
async def test_path_isolation_between_sandboxes(executor, config):
    """沙箱 A 写入的文件不能在沙箱 B 中读取（路径隔离）"""
    info_a = await executor.create(config)
    info_b = await executor.create(config)

    await executor.files_write(info_a.sandbox_id, "/tmp/secret.txt", "secret_a")

    # 沙箱 B 中该路径不存在
    with pytest.raises(FileNotFoundError):
        await executor.files_read(info_b.sandbox_id, "/tmp/secret.txt")

    await executor.destroy(info_a.sandbox_id)
    await executor.destroy(info_b.sandbox_id)


# ── pause / resume ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pause_blocks_execute(executor, config):
    info = await executor.create(config)
    await executor.pause(info.sandbox_id)
    with pytest.raises(SandboxDestroyedError):
        await executor.execute(info.sandbox_id, "print('hi')")
    # cleanup（直接删注册表，绕过 assert_alive）
    _MOCK_REGISTRY.pop(info.sandbox_id, None)


@pytest.mark.asyncio
async def test_resume_after_pause(executor, config):
    info = await executor.create(config)
    await executor.pause(info.sandbox_id)
    await executor.resume(info.sandbox_id)
    result = await executor.execute(info.sandbox_id, "print('resumed')")
    assert "resumed" in result.stdout
    await executor.destroy(info.sandbox_id)


# ── destroy 幂等性 ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_destroy_is_idempotent(executor, config):
    info = await executor.create(config)
    await executor.destroy(info.sandbox_id)
    # 再次销毁不应抛出异常
    await executor.destroy(info.sandbox_id)
    assert info.sandbox_id not in _MOCK_REGISTRY


# ── TTL 验证 ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_connect_info_is_expired_when_timeout_at_is_past(executor):
    """ConnectInfo.is_expired 在 timeout_at 过期时返回 True"""
    from agent_forge.sandbox.base import ConnectInfo, SandboxState

    # 模拟过期：timeout_at 设为 1 秒前
    info = ConnectInfo(
        sandbox_id="mock-test",
        host="127.0.0.1",
        port=0,
        template_id="mock",
        state=SandboxState.RUNNING,
        timeout_at=int(time.time()) - 1,
    )
    assert info.is_expired is True


@pytest.mark.asyncio
async def test_connect_info_not_expired_when_timeout_at_is_future(executor):
    from agent_forge.sandbox.base import ConnectInfo, SandboxState

    info = ConnectInfo(
        sandbox_id="mock-test",
        host="127.0.0.1",
        port=0,
        template_id="mock",
        state=SandboxState.RUNNING,
        timeout_at=int(time.time()) + 3600,
    )
    assert info.is_expired is False
