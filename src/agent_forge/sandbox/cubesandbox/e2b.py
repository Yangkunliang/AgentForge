"""
agent_forge.sandbox.cubesandbox.e2b
=====================================
CubeSandboxE2BExecutor：基于 E2B SDK 的 CubeSandbox 执行器（推荐路径）。

CubeSandbox 完全兼容 E2B SDK，仅需设置两个环境变量指向自部署实例：
    E2B_DOMAIN         = ""                      # 禁用默认 E2B 云域名
    E2B_DATA_PLANE_URL = http://127.0.0.1:3000   # 自部署 CubeSandbox 地址

依赖
----
pip install e2b-code-interpreter

兼容性说明
----------
- e2b-code-interpreter < 1.x：同步 SDK，通过 _SANDBOX_THREAD_POOL 桥接 asyncio
- e2b-code-interpreter >= 1.x（若提供 AsyncSandbox）：可直接 await，
  届时移除 run_in_executor 调用和 _SANDBOX_THREAD_POOL
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

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

# 专用线程池：避免与 FastAPI 默认线程池争抢资源
# E2B SDK 当前版本核心方法是同步阻塞的，需通过线程池桥接 asyncio
_SANDBOX_THREAD_POOL = ThreadPoolExecutor(
    max_workers=20,
    thread_name_prefix="cube-sandbox-e2b",
)

_E2B_REGISTRY: dict[str, dict] = {}


class CubeSandboxE2BExecutor:
    """基于 E2B SDK 的 CubeSandbox 执行器。

    Args:
        api_url:     CubeSandbox API 地址，默认读取 CUBE_SANDBOX_URL
        api_key:     API Key，默认读取 CUBE_SANDBOX_API_KEY
        template_id: 默认模板 ID，默认读取 CUBE_TEMPLATE_ID
    """

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        template_id: str | None = None,
    ) -> None:
        self._api_url = api_url or os.environ.get(
            "CUBE_SANDBOX_URL", "http://127.0.0.1:3000"
        )
        self._api_key = api_key or os.environ.get("CUBE_SANDBOX_API_KEY", "")
        self._template_id = template_id or os.environ.get("CUBE_TEMPLATE_ID", "")

        # 指向自部署 CubeSandbox，禁用 E2B 默认云域名
        os.environ["E2B_DOMAIN"] = ""
        os.environ["E2B_DATA_PLANE_URL"] = self._api_url

    def _import_sdk(self):
        """懒加载 E2B SDK，提供清晰的错误提示。"""
        try:
            from e2b_code_interpreter import Sandbox  # noqa: PLC0415
            return Sandbox
        except ImportError as e:
            raise SandboxUnavailableError(
                "e2b-code-interpreter 未安装，请执行: pip install e2b-code-interpreter"
            ) from e

    async def _run_in_thread(self, fn):
        """在专用线程池中运行同步函数。"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_SANDBOX_THREAD_POOL, fn)

    async def create(self, config: SandboxConfig) -> ConnectInfo:
        E2BSandbox = self._import_sdk()
        tpl = config.template_id or self._template_id

        try:
            sandbox = await self._run_in_thread(
                lambda: E2BSandbox.create(template=tpl, api_key=self._api_key)
            )
        except Exception as e:
            raise SandboxUnavailableError(f"CubeSandbox 创建失败: {e}") from e

        _E2B_REGISTRY[sandbox.sandbox_id] = {
            "state": SandboxState.RUNNING,
            "template_id": tpl,
            "created_at": time.time(),
        }
        logger.info("[CubeSandbox/E2B] created sandbox_id=%s", sandbox.sandbox_id)
        return ConnectInfo(
            sandbox_id=sandbox.sandbox_id,
            host=sandbox.get_host(),   # 纯 hostname/IP，不含端口
            port=config.exposed_ports[0] if config.exposed_ports else 49999,
            template_id=tpl,
        )

    async def execute(
        self, sandbox_id: str, code: str, timeout: int = 30
    ) -> ExecResult:
        E2BSandbox = self._import_sdk()
        start = time.monotonic()

        def _exec():
            sbx = E2BSandbox.attach(sandbox_id, api_key=self._api_key)
            return sbx.run_code(code, timeout=timeout)

        try:
            result = await self._run_in_thread(_exec)
        except TimeoutError as e:
            raise SandboxTimeoutError(
                f"[CubeSandbox/E2B] 代码执行超时（{timeout}s）"
            ) from e
        except Exception as e:
            raise SandboxUnavailableError(
                f"[CubeSandbox/E2B] execute 失败: {e}"
            ) from e

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return ExecResult(
            stdout="".join(
                r.text for r in result.results if hasattr(r, "text")
            ),
            stderr=result.error.traceback if result.error else "",
            exit_code=0 if result.error is None else 1,
            duration_ms=elapsed_ms,
        )

    async def execute_shell(
        self, sandbox_id: str, command: str, timeout: int = 30
    ) -> ExecResult:
        E2BSandbox = self._import_sdk()
        start = time.monotonic()

        def _exec():
            sbx = E2BSandbox.attach(sandbox_id, api_key=self._api_key)
            return sbx.process.start_and_wait(command, timeout=timeout)

        try:
            result = await self._run_in_thread(_exec)
        except TimeoutError as e:
            raise SandboxTimeoutError(
                f"[CubeSandbox/E2B] Shell 执行超时（{timeout}s）"
            ) from e

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return ExecResult(
            stdout=result.stdout or "",
            stderr=result.stderr or "",
            exit_code=result.exit_code or 0,
            duration_ms=elapsed_ms,
        )

    async def files_read(self, sandbox_id: str, path: str) -> str:
        E2BSandbox = self._import_sdk()

        def _read():
            sbx = E2BSandbox.attach(sandbox_id, api_key=self._api_key)
            return sbx.files.read(path)

        return await self._run_in_thread(_read)

    async def files_write(
        self, sandbox_id: str, path: str, content: str
    ) -> None:
        E2BSandbox = self._import_sdk()

        def _write():
            sbx = E2BSandbox.attach(sandbox_id, api_key=self._api_key)
            sbx.files.write(path, content)

        await self._run_in_thread(_write)

    async def connect(self, sandbox_id: str, timeout: int = 0) -> ConnectInfo:
        meta = _E2B_REGISTRY.get(sandbox_id, {})
        return ConnectInfo(
            sandbox_id=sandbox_id,
            host="127.0.0.1",
            port=49999,
            template_id=meta.get("template_id", ""),
        )

    async def get_logs(self, sandbox_id: str) -> str:
        return ""  # E2B SDK 不提供历史日志接口

    async def pause(self, sandbox_id: str) -> None:
        if sandbox_id in _E2B_REGISTRY:
            _E2B_REGISTRY[sandbox_id]["state"] = SandboxState.PAUSED

    async def resume(self, sandbox_id: str, timeout: int = 0) -> ConnectInfo:
        if sandbox_id not in _E2B_REGISTRY:
            raise SandboxDestroyedError(
                f"[CubeSandbox/E2B] 沙箱不存在: {sandbox_id}"
            )
        _E2B_REGISTRY[sandbox_id]["state"] = SandboxState.RUNNING
        return await self.connect(sandbox_id)

    async def destroy(self, sandbox_id: str) -> None:
        E2BSandbox = self._import_sdk()
        try:
            await self._run_in_thread(
                lambda: E2BSandbox.attach(
                    sandbox_id, api_key=self._api_key
                ).close()
            )
        except Exception as e:
            logger.warning(
                "[CubeSandbox/E2B] destroy 失败（可能已销毁）: %s", e
            )
        _E2B_REGISTRY.pop(sandbox_id, None)
        logger.info("[CubeSandbox/E2B] destroyed sandbox_id=%s", sandbox_id)
