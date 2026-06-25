"""
agent_forge.sandbox.mock
=========================
MockSandboxExecutor：本地开发 & 单元测试用沙箱执行器。

特性
----
- 无需 KVM / Docker，直接用 asyncio.subprocess 在宿主机执行代码
- 不做任何隔离，仅用于开发调试和 CI 单元测试
- 通过 CUBE_SANDBOX_DEFAULT_PROVIDER=mock 启用

⚠️  安全警告：MockSandboxExecutor 不提供任何隔离，绝对不能用于生产环境。
    生产环境必须使用 DockerSandboxExecutor 或 CubeSandboxExecutor。
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid

from agent_forge.sandbox.base import (
    ConnectInfo,
    ExecResult,
    SandboxConfig,
    SandboxDestroyedError,
    SandboxState,
    SandboxTimeoutError,
)

logger = logging.getLogger(__name__)

# 内存中维护的"沙箱"注册表（sandbox_id → metadata）
_MOCK_REGISTRY: dict[str, dict] = {}


class MockSandboxExecutor:
    """Mock 沙箱执行器，用于本地开发和单元测试。

    不做进程隔离，直接在当前 Python 进程的子进程中执行代码。
    sandbox_id 仅作为标识符，不对应真实隔离环境。

    用法：
        executor = MockSandboxExecutor()
        manager  = SandboxManager(executor, ttl_seconds=60)
        result   = await manager.execute("print(1 + 1)")
        # stdout == "2\\n"
    """

    # ── SandboxExecutor Protocol 实现 ─────────────────────────────────────────

    async def create(self, config: SandboxConfig) -> ConnectInfo:
        sandbox_id = f"mock-{uuid.uuid4().hex[:8]}"
        _MOCK_REGISTRY[sandbox_id] = {
            "state": SandboxState.RUNNING,
            "created_at": time.time(),
            "template_id": config.template_id or "mock",
            "files": {},          # path → content，模拟沙箱文件系统
        }
        logger.debug("[MockSandbox] created sandbox_id=%s", sandbox_id)
        return ConnectInfo(
            sandbox_id=sandbox_id,
            host="127.0.0.1",
            port=0,               # mock 不监听端口
            template_id=config.template_id or "mock",
        )

    async def execute(
        self, sandbox_id: str, code: str, timeout: int = 30
    ) -> ExecResult:
        self._assert_alive(sandbox_id)
        logger.debug("[MockSandbox] execute sandbox_id=%s", sandbox_id)
        return await self._run_subprocess(
            ["python3", "-c", code], timeout=timeout
        )

    async def execute_shell(
        self, sandbox_id: str, command: str, timeout: int = 30
    ) -> ExecResult:
        self._assert_alive(sandbox_id)
        logger.debug("[MockSandbox] execute_shell sandbox_id=%s cmd=%r", sandbox_id, command)
        return await self._run_subprocess(
            ["bash", "-c", command], timeout=timeout
        )

    async def files_read(self, sandbox_id: str, path: str) -> str:
        self._assert_alive(sandbox_id)
        files = _MOCK_REGISTRY[sandbox_id]["files"]
        if path not in files:
            raise FileNotFoundError(f"[MockSandbox] 文件不存在: {path}")
        return files[path]

    async def files_write(
        self, sandbox_id: str, path: str, content: str
    ) -> None:
        self._assert_alive(sandbox_id)
        _MOCK_REGISTRY[sandbox_id]["files"][path] = content

    async def connect(self, sandbox_id: str, timeout: int = 0) -> ConnectInfo:
        self._assert_alive(sandbox_id)
        meta = _MOCK_REGISTRY[sandbox_id]
        return ConnectInfo(
            sandbox_id=sandbox_id,
            host="127.0.0.1",
            port=0,
            template_id=meta["template_id"],
        )

    async def get_logs(self, sandbox_id: str) -> str:
        self._assert_alive(sandbox_id)
        return ""  # mock 不保留历史日志

    async def pause(self, sandbox_id: str) -> None:
        if sandbox_id in _MOCK_REGISTRY:
            _MOCK_REGISTRY[sandbox_id]["state"] = SandboxState.PAUSED
            logger.debug("[MockSandbox] paused sandbox_id=%s", sandbox_id)

    async def resume(
        self, sandbox_id: str, timeout: int = 0
    ) -> ConnectInfo:
        if sandbox_id not in _MOCK_REGISTRY:
            raise SandboxDestroyedError(f"[MockSandbox] 沙箱不存在: {sandbox_id}")
        _MOCK_REGISTRY[sandbox_id]["state"] = SandboxState.RUNNING
        meta = _MOCK_REGISTRY[sandbox_id]
        return ConnectInfo(
            sandbox_id=sandbox_id,
            host="127.0.0.1",
            port=0,
            template_id=meta["template_id"],
        )

    async def destroy(self, sandbox_id: str) -> None:
        _MOCK_REGISTRY.pop(sandbox_id, None)
        logger.debug("[MockSandbox] destroyed sandbox_id=%s", sandbox_id)

    # ── 内部辅助 ─────────────────────────────────────────────────────────────

    def _assert_alive(self, sandbox_id: str) -> None:
        if sandbox_id not in _MOCK_REGISTRY:
            raise SandboxDestroyedError(
                f"[MockSandbox] 沙箱不存在或已销毁: {sandbox_id}"
            )
        state = _MOCK_REGISTRY[sandbox_id]["state"]
        if state == SandboxState.PAUSED:
            raise SandboxDestroyedError(
                f"[MockSandbox] 沙箱已暂停，请先 resume: {sandbox_id}"
            )

    @staticmethod
    async def _run_subprocess(
        cmd: list[str], timeout: int
    ) -> ExecResult:
        """在子进程中执行命令，返回 ExecResult。"""
        start = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=float(timeout)
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                raise SandboxTimeoutError(
                    f"[MockSandbox] 执行超时（{timeout}s）: {' '.join(cmd)}"
                )
        except FileNotFoundError as e:
            raise RuntimeError(f"[MockSandbox] 命令不存在: {e}") from e

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return ExecResult(
            stdout=stdout_bytes.decode(errors="replace"),
            stderr=stderr_bytes.decode(errors="replace"),
            exit_code=proc.returncode or 0,
            duration_ms=elapsed_ms,
        )
