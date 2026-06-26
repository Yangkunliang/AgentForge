"""
tests/sandbox/test_api_executor.py
===================================
CubeSandboxAPIExecutor 单元测试（mock HTTP）

覆盖场景
--------
- create / execute / execute_shell / files_read / files_write
- connect / get_logs / pause / resume / destroy
- 异常映射：401→AuthError, 404→DestroyedError, 409→CreationError, 500→UnavailableError
- close
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import Response

from agent_forge.sandbox.base import (
    SandboxConfig,
    SandboxAuthError,
    SandboxCreationError,
    SandboxDestroyedError,
    SandboxTimeoutError,
    SandboxUnavailableError,
)
from agent_forge.sandbox.cubesandbox.api import CubeSandboxAPIExecutor


# ── 夹具 ─────────────────────────────────────────────────────────────


def _make_response(status_code: int, json_data: dict = None) -> Response:
    return Response(status_code, json=json_data, request=MagicMock())


@pytest.fixture
def executor():
    return CubeSandboxAPIExecutor(
        base_url="http://127.0.0.1:3000",
        api_key="test-key",
    )


# ── _raise_for_status ────────────────────────────────────────────────


def test_raise_for_status_401():
    """401 → SandboxAuthError"""
    executor = CubeSandboxAPIExecutor("http://x", "bad-key")
    resp = _make_response(401)
    with pytest.raises(SandboxAuthError):
        executor._raise_for_status(resp)


def test_raise_for_status_404():
    """404 → SandboxDestroyedError"""
    executor = CubeSandboxAPIExecutor("http://x", "key")
    resp = _make_response(404)
    with pytest.raises(SandboxDestroyedError):
        executor._raise_for_status(resp)


def test_raise_for_status_409():
    """409 → SandboxCreationError"""
    executor = CubeSandboxAPIExecutor("http://x", "key")
    resp = _make_response(409, {"error": "conflict"})
    with pytest.raises(SandboxCreationError):
        executor._raise_for_status(resp)


def test_raise_for_status_500():
    """500 → SandboxUnavailableError"""
    executor = CubeSandboxAPIExecutor("http://x", "key")
    resp = _make_response(500)
    with pytest.raises(SandboxUnavailableError):
        executor._raise_for_status(resp)


def test_raise_for_status_200():
    """200 不抛异常"""
    executor = CubeSandboxAPIExecutor("http://x", "key")
    resp = _make_response(200, {"ok": True})
    executor._raise_for_status(resp)  # should not raise


# ── create ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_success(executor):
    """成功创建沙箱"""
    resp_data = {"sandboxID": "sb-123", "host": "10.0.0.1", "port": 49999}
    executor._client.post = AsyncMock(return_value=_make_response(200, resp_data))

    config = SandboxConfig(template_id="tpl-py", timeout_seconds=300)
    info = await executor.create(config)

    assert info.sandbox_id == "sb-123"
    assert info.host == "10.0.0.1"
    assert info.port == 49999
    assert info.template_id == "tpl-py"
    executor._client.post.assert_called_once_with("/sandboxes", json={
        "templateID": "tpl-py",
        "timeout": 300,
    })


@pytest.mark.asyncio
async def test_create_default_template(executor):
    """不传 template_id 时使用空字符串"""
    executor._client.post = AsyncMock(return_value=_make_response(200, {
        "sandboxID": "sb-1", "host": "10.0.0.1", "port": 80,
    }))
    info = await executor.create(SandboxConfig())
    assert info.sandbox_id == "sb-1"


# ── execute ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_execute_success(executor):
    """成功执行 Python 代码"""
    executor._client.post = AsyncMock(return_value=_make_response(200, {
        "stdout": "hello\n",
        "stderr": "",
        "exitCode": 0,
        "timedOut": False,
        "durationMs": 50,
    }))

    result = await executor.execute("sb-1", "print('hello')")
    assert result.stdout.strip() == "hello"
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_execute_timeout(executor):
    """执行超时抛出 SandboxTimeoutError"""
    executor._client.post = AsyncMock(return_value=_make_response(200, {
        "timedOut": True,
    }))

    with pytest.raises(SandboxTimeoutError):
        await executor.execute("sb-1", "import time; time.sleep(100)")


# ── execute_shell ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_execute_shell_success(executor):
    """成功执行 Shell 命令"""
    executor._client.post = AsyncMock(return_value=_make_response(200, {
        "stdout": "world\n",
        "stderr": "",
        "exitCode": 0,
        "timedOut": False,
    }))

    result = await executor.execute_shell("sb-1", "echo world")
    assert result.stdout.strip() == "world"
    assert result.exit_code == 0


# ── files ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_files_write(executor):
    executor._client.post = AsyncMock(return_value=_make_response(200))
    await executor.files_write("sb-1", "/tmp/hello.txt", "content")
    executor._client.post.assert_called_once()
    call_args = executor._client.post.call_args
    assert call_args[0][0] == "/sandboxes/sb-1/files/write"
    assert call_args[1]["json"] == {"path": "/tmp/hello.txt", "content": "content"}


@pytest.mark.asyncio
async def test_files_read(executor):
    executor._client.post = AsyncMock(return_value=_make_response(200, {"content": "hello"}))
    content = await executor.files_read("sb-1", "/tmp/hello.txt")
    assert content == "hello"


# ── connect / get_logs / pause / resume / destroy ─────────────────────


@pytest.mark.asyncio
async def test_connect(executor):
    executor._client.post = AsyncMock(return_value=_make_response(200, {
        "host": "10.0.0.1", "port": 49999,
    }))
    info = await executor.connect("sb-1")
    assert info.sandbox_id == "sb-1"


@pytest.mark.asyncio
async def test_get_logs(executor):
    executor._client.get = AsyncMock(return_value=_make_response(200, {"logs": "log data"}))
    logs = await executor.get_logs("sb-1")
    assert logs == "log data"
    executor._client.get.assert_called_once_with("/sandboxes/sb-1/logs")


@pytest.mark.asyncio
async def test_pause(executor):
    executor._client.post = AsyncMock(return_value=_make_response(200))
    await executor.pause("sb-1")


@pytest.mark.asyncio
async def test_resume(executor):
    executor._client.post = AsyncMock(return_value=_make_response(200, {
        "host": "10.0.0.1", "port": 49999,
    }))
    info = await executor.resume("sb-1")
    assert info.host == "10.0.0.1"


@pytest.mark.asyncio
async def test_destroy(executor):
    executor._client.delete = AsyncMock(return_value=_make_response(200))
    await executor.destroy("sb-1")
    executor._client.delete.assert_called_once_with("/sandboxes/sb-1")


@pytest.mark.asyncio
async def test_destroy_404_is_not_fatal(executor):
    """destroy 返回 404 时不应抛出异常"""
    executor._client.delete = AsyncMock(return_value=_make_response(404))
    await executor.destroy("sb-1")  # should not raise


@pytest.mark.asyncio
async def test_close(executor):
    executor._client.aclose = AsyncMock()
    await executor.close()
    executor._client.aclose.assert_called_once()
