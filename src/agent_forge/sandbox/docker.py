"""
agent_forge.sandbox.docker
===========================
DockerSandboxExecutor：基于 Docker 容器的沙箱执行器（现有方案）。

隔离级别：Namespace + Cgroup（容器级）
适用场景：可信代码执行（用户自己的项目代码）
不适用：LLM 生成的不可信代码（应使用 CubeSandboxExecutor）

安全配置
--------
- network_disabled=True：禁止容器访问网络
- read_only=True：只读文件系统，/tmp 挂载 tmpfs
- user="nobody"：非 root 用户运行
- no-new-privileges：禁止提权
- 30s 执行超时，256MB 内存上限

依赖
----
pip install docker
"""

from __future__ import annotations

import logging
import tempfile
import time
import uuid

from agent_forge.sandbox.base import (
    ConnectInfo,
    ExecResult,
    SandboxConfig,
    SandboxDestroyedError,
    SandboxState,
    SandboxTimeoutError,
    SandboxUnavailableError,
)

logger = logging.getLogger(__name__)

# 内存中维护 sandbox_id → container_id 的映射
_DOCKER_REGISTRY: dict[str, dict] = {}


class DockerSandboxExecutor:
    """Docker 容器沙箱执行器。

    每次 execute() 启动一次性容器，执行后自动删除（remove=True）。
    不维护长生命周期容器，适合短时代码执行场景。
    """

    DEFAULT_IMAGE = "python:3.11-slim"
    DEFAULT_MEMORY = "256m"
    DEFAULT_CPU_QUOTA = 50000   # 50% CPU

    def __init__(
        self,
        image: str = DEFAULT_IMAGE,
        memory_limit: str = DEFAULT_MEMORY,
        cpu_quota: int = DEFAULT_CPU_QUOTA,
    ) -> None:
        self._image = image
        self._memory_limit = memory_limit
        self._cpu_quota = cpu_quota
        self._client = None  # 懒加载，避免 import 时连接 Docker

    def _get_client(self):
        if self._client is None:
            try:
                import docker  # noqa: PLC0415
                self._client = docker.from_env()
            except ImportError as e:
                raise SandboxUnavailableError(
                    "docker 包未安装，请执行: pip install docker"
                ) from e
            except Exception as e:
                raise SandboxUnavailableError(
                    f"无法连接 Docker daemon: {e}"
                ) from e
        return self._client

    async def create(self, config: SandboxConfig) -> ConnectInfo:
        # Docker 方案不预创建容器，sandbox_id 仅作为标识符
        sandbox_id = f"docker-{uuid.uuid4().hex[:8]}"
        _DOCKER_REGISTRY[sandbox_id] = {
            "state": SandboxState.RUNNING,
            "image": self._image,
            "created_at": time.time(),
        }
        logger.debug("[DockerSandbox] registered sandbox_id=%s", sandbox_id)
        return ConnectInfo(
            sandbox_id=sandbox_id,
            host="127.0.0.1",
            port=0,
            template_id=config.template_id or self._image,
        )

    async def execute(
        self, sandbox_id: str, code: str, timeout: int = 30
    ) -> ExecResult:
        self._assert_alive(sandbox_id)
        client = self._get_client()

        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(code)
            script_path = f.name

        script_name = script_path.split("/")[-1]
        start = time.monotonic()

        try:
            import asyncio  # noqa: PLC0415
            container = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.containers.run(
                    image=self._image,
                    command=f"python /code/{script_name}",
                    volumes={script_path: {"bind": f"/code/{script_name}", "mode": "ro"}},
                    network_disabled=True,
                    mem_limit=self._memory_limit,
                    cpu_quota=self._cpu_quota,
                    read_only=True,
                    tmpfs={"/tmp": "size=64m"},
                    user="nobody",
                    security_opt=["no-new-privileges:true"],
                    remove=True,
                    detach=True,
                ),
            )
            try:
                exit_code_result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, lambda: container.wait(timeout=timeout)
                    ),
                    timeout=timeout + 2,
                )
                stdout = container.logs(stdout=True, stderr=False).decode(errors="replace")
                stderr = container.logs(stdout=False, stderr=True).decode(errors="replace")
                exit_code = exit_code_result.get("StatusCode", 0)
            except (asyncio.TimeoutError, Exception):
                try:
                    container.kill()
                except Exception:
                    pass
                raise SandboxTimeoutError(
                    f"[DockerSandbox] 代码执行超时（{timeout}s）"
                )
        except SandboxTimeoutError:
            raise
        except Exception as e:
            raise SandboxUnavailableError(f"[DockerSandbox] 容器执行失败: {e}") from e

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return ExecResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            duration_ms=elapsed_ms,
        )

    async def execute_shell(
        self, sandbox_id: str, command: str, timeout: int = 30
    ) -> ExecResult:
        # 将 shell 命令包装成 python 调用，复用 execute() 的隔离配置
        code = (
            "import subprocess, sys\n"
            f"r = subprocess.run({command!r}, shell=True, capture_output=True, text=True)\n"
            "sys.stdout.write(r.stdout)\n"
            "sys.stderr.write(r.stderr)\n"
            "sys.exit(r.returncode)\n"
        )
        return await self.execute(sandbox_id, code, timeout=timeout)

    async def files_read(self, sandbox_id: str, path: str) -> str:
        raise NotImplementedError(
            "DockerSandboxExecutor 不支持 files_read（一次性容器，无持久文件系统）"
        )

    async def files_write(self, sandbox_id: str, path: str, content: str) -> None:
        raise NotImplementedError(
            "DockerSandboxExecutor 不支持 files_write（一次性容器，无持久文件系统）"
        )

    async def connect(self, sandbox_id: str, timeout: int = 0) -> ConnectInfo:
        self._assert_alive(sandbox_id)
        meta = _DOCKER_REGISTRY[sandbox_id]
        return ConnectInfo(
            sandbox_id=sandbox_id,
            host="127.0.0.1",
            port=0,
            template_id=meta["image"],
        )

    async def get_logs(self, sandbox_id: str) -> str:
        return ""  # 一次性容器，不保留历史日志

    async def pause(self, sandbox_id: str) -> None:
        if sandbox_id in _DOCKER_REGISTRY:
            _DOCKER_REGISTRY[sandbox_id]["state"] = SandboxState.PAUSED

    async def resume(self, sandbox_id: str, timeout: int = 0) -> ConnectInfo:
        self._assert_alive(sandbox_id)
        _DOCKER_REGISTRY[sandbox_id]["state"] = SandboxState.RUNNING
        return await self.connect(sandbox_id)

    async def destroy(self, sandbox_id: str) -> None:
        _DOCKER_REGISTRY.pop(sandbox_id, None)
        logger.debug("[DockerSandbox] destroyed sandbox_id=%s", sandbox_id)

    def _assert_alive(self, sandbox_id: str) -> None:
        if sandbox_id not in _DOCKER_REGISTRY:
            raise SandboxDestroyedError(
                f"[DockerSandbox] 沙箱不存在或已销毁: {sandbox_id}"
            )
