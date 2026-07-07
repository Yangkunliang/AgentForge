"""Test-only sandbox executor fakes.

These fakes keep sandbox unit tests offline without reintroducing the removed
runtime MockSandboxExecutor provider.
"""

from __future__ import annotations

import asyncio
import itertools
import sys
import time
from dataclasses import dataclass, field

from agent_forge.sandbox.base import (
    ConnectInfo,
    ExecResult,
    SandboxConfig,
    SandboxDestroyedError,
    SandboxState,
    SandboxTimeoutError,
)


@dataclass
class _SandboxRecord:
    info: ConnectInfo
    files: dict[str, str] = field(default_factory=dict)
    logs: list[str] = field(default_factory=list)


_ID_COUNTER = itertools.count(1)
_TEST_SANDBOX_REGISTRY: dict[str, _SandboxRecord] = {}


class InMemorySandboxExecutor:
    """Protocol-compatible fake executor for unit tests."""

    async def create(self, config: SandboxConfig) -> ConnectInfo:
        sandbox_id = f"test-sandbox-{next(_ID_COUNTER)}"
        timeout_at = (
            int(time.time()) + config.timeout_seconds
            if config.timeout_seconds > 0
            else 0
        )
        info = ConnectInfo(
            sandbox_id=sandbox_id,
            host="127.0.0.1",
            port=0,
            template_id=config.template_id or "test",
            state=SandboxState.RUNNING,
            timeout_at=timeout_at,
        )
        _TEST_SANDBOX_REGISTRY[sandbox_id] = _SandboxRecord(info=info)
        return info

    async def execute(
        self, sandbox_id: str, code: str, timeout: int = 30
    ) -> ExecResult:
        record = self._assert_running(sandbox_id)
        started_at = time.monotonic()
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except TimeoutError as exc:
            proc.kill()
            await proc.wait()
            raise SandboxTimeoutError(f"Execution timed out after {timeout}s") from exc

        duration_ms = int((time.monotonic() - started_at) * 1000)
        result = ExecResult(
            stdout=stdout.decode(),
            stderr=stderr.decode(),
            exit_code=proc.returncode or 0,
            duration_ms=duration_ms,
        )
        record.logs.append(result.stdout + result.stderr)
        return result

    async def execute_shell(
        self, sandbox_id: str, command: str, timeout: int = 30
    ) -> ExecResult:
        record = self._assert_running(sandbox_id)
        started_at = time.monotonic()
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except TimeoutError as exc:
            proc.kill()
            await proc.wait()
            raise SandboxTimeoutError(f"Shell timed out after {timeout}s") from exc

        duration_ms = int((time.monotonic() - started_at) * 1000)
        result = ExecResult(
            stdout=stdout.decode(),
            stderr=stderr.decode(),
            exit_code=proc.returncode or 0,
            duration_ms=duration_ms,
        )
        record.logs.append(result.stdout + result.stderr)
        return result

    async def files_read(self, sandbox_id: str, path: str) -> str:
        record = self._assert_running(sandbox_id)
        if path not in record.files:
            raise FileNotFoundError(path)
        return record.files[path]

    async def files_write(self, sandbox_id: str, path: str, content: str) -> None:
        record = self._assert_running(sandbox_id)
        record.files[path] = content

    async def connect(self, sandbox_id: str, timeout: int = 0) -> ConnectInfo:
        record = self._get_record(sandbox_id)
        if record.info.state == SandboxState.DESTROYED:
            raise SandboxDestroyedError(f"Sandbox {sandbox_id} is destroyed")
        if timeout > 0:
            record.info.timeout_at = int(time.time()) + timeout
        return record.info

    async def get_logs(self, sandbox_id: str) -> str:
        record = self._get_record(sandbox_id)
        return "".join(record.logs)

    async def pause(self, sandbox_id: str) -> None:
        record = self._assert_running(sandbox_id)
        record.info.state = SandboxState.PAUSED

    async def resume(self, sandbox_id: str, timeout: int = 0) -> ConnectInfo:
        record = self._get_record(sandbox_id)
        if record.info.state == SandboxState.DESTROYED:
            raise SandboxDestroyedError(f"Sandbox {sandbox_id} is destroyed")
        record.info.state = SandboxState.RUNNING
        if timeout > 0:
            record.info.timeout_at = int(time.time()) + timeout
        return record.info

    async def destroy(self, sandbox_id: str) -> None:
        _TEST_SANDBOX_REGISTRY.pop(sandbox_id, None)

    def _get_record(self, sandbox_id: str) -> _SandboxRecord:
        record = _TEST_SANDBOX_REGISTRY.get(sandbox_id)
        if record is None:
            raise SandboxDestroyedError(f"Sandbox {sandbox_id} is destroyed")
        return record

    def _assert_running(self, sandbox_id: str) -> _SandboxRecord:
        record = self._get_record(sandbox_id)
        if record.info.state != SandboxState.RUNNING:
            raise SandboxDestroyedError(f"Sandbox {sandbox_id} is not running")
        return record
