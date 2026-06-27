"""
agent_forge.sandbox.cubesandbox.e2b
=====================================
CubeSandboxE2BExecutor：基于 E2B SDK v1 的沙箱执行器。

支持两种部署模式，通过环境变量区分：

  E2B 云服务（开发 & 生产均可用）：
    E2B_API_KEY=e2b_xxx        # 在 https://e2b.dev 注册后免费获取
    CUBE_SANDBOX_URL 不设置    # 不设置则默认使用 E2B 云

  自部署 CubeSandbox（私有化部署）：
    E2B_API_KEY=e2b_xxx
    CUBE_SANDBOX_URL=http://your-cube-host:3000

依赖
----
pip install "e2b-code-interpreter>=1.0.0"

SDK v1 特性
-----------
- AsyncSandbox 原生 async/await，无需线程池桥接
- run_code() / commands.run() 均为 async 方法
- sandbox.kill() 替代旧版 close()
"""

from __future__ import annotations

import logging
import os
import time

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

# sandbox_id → 元数据（state、template_id、created_at）
_E2B_REGISTRY: dict[str, dict] = {}


class CubeSandboxE2BExecutor:
    """基于 E2B SDK v1 的沙箱执行器。

    开发和生产环境共用同一套代码，通过环境变量选择接入 E2B 云或自部署 CubeSandbox。

    Args:
        api_key:     E2B API Key，默认读取 E2B_API_KEY
        api_url:     自部署 CubeSandbox 地址，不设置则使用 E2B 云
        template_id: 默认沙箱模板 ID，默认读取 CUBE_TEMPLATE_ID
    """

    def __init__(
        self,
        api_url: str | None = None,
        template_id: str | None = None,
    ) -> None:
        self._api_key = os.environ.get("E2B_API_KEY", "")
        self._api_url = api_url or os.environ.get("CUBE_SANDBOX_URL", "")
        self._template_id = template_id or os.environ.get("CUBE_TEMPLATE_ID", "")

        if not self._api_key:
            raise SandboxUnavailableError(
                "E2B API Key 未配置，请设置环境变量 E2B_API_KEY。"
                "访问 https://e2b.dev 注册后可免费获取。"
            )

        # 自部署模式：通过 E2B_DOMAIN 指向本地 CubeSandbox
        if self._api_url:
            os.environ["E2B_DOMAIN"] = self._api_url
            logger.info("[E2B] 自部署模式 → %s", self._api_url)
        else:
            logger.info("[E2B] 云服务模式 → e2b.dev")

    def _sdk(self):
        """懒加载 AsyncSandbox，提供清晰的安装提示。"""
        try:
            from e2b_code_interpreter import AsyncSandbox  # noqa: PLC0415
            return AsyncSandbox
        except ImportError as exc:
            raise SandboxUnavailableError(
                "e2b-code-interpreter 未安装，请执行: "
                "pip install 'e2b-code-interpreter>=1.0.0'"
            ) from exc

    # ── SandboxExecutor Protocol 实现 ─────────────────────────────────────────

    async def create(self, config: SandboxConfig) -> ConnectInfo:
        AsyncSandbox = self._sdk()
        tpl = config.template_id or self._template_id or None

        try:
            sandbox = await AsyncSandbox.create(
                template=tpl,
                api_key=self._api_key,
                timeout=config.timeout_seconds,
            )
        except Exception as exc:
            raise SandboxUnavailableError(f"[E2B] 沙箱创建失败: {exc}") from exc

        _E2B_REGISTRY[sandbox.sandbox_id] = {
            "state": SandboxState.RUNNING,
            "template_id": tpl or "",
            "created_at": time.time(),
        }
        logger.info("[E2B] created sandbox_id=%s template=%s", sandbox.sandbox_id, tpl)
        return ConnectInfo(
            sandbox_id=sandbox.sandbox_id,
            host="",
            port=0,
            template_id=tpl or "",
        )

    async def execute(self, sandbox_id: str, code: str, timeout: int = 30) -> ExecResult:
        AsyncSandbox = self._sdk()
        self._assert_alive(sandbox_id)
        start = time.monotonic()

        try:
            sandbox = await AsyncSandbox.connect(sandbox_id, api_key=self._api_key)
            result = await sandbox.run_code(code, timeout=float(timeout))
        except TimeoutError as exc:
            raise SandboxTimeoutError(f"[E2B] 代码执行超时（{timeout}s）") from exc
        except Exception as exc:
            raise SandboxUnavailableError(f"[E2B] execute 失败: {exc}") from exc

        elapsed_ms = int((time.monotonic() - start) * 1000)

        # v1 SDK：stdout/stderr 在 result.logs 里，result.results 是 Jupyter cell 输出
        stdout = "\n".join(result.logs.stdout) if result.logs.stdout else ""
        stderr = "\n".join(result.logs.stderr) if result.logs.stderr else ""
        if result.error:
            stderr = (stderr + "\n" + result.error.traceback).strip()

        return ExecResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=0 if result.error is None else 1,
            duration_ms=elapsed_ms,
        )

    async def execute_shell(self, sandbox_id: str, command: str, timeout: int = 30) -> ExecResult:
        AsyncSandbox = self._sdk()
        self._assert_alive(sandbox_id)
        start = time.monotonic()

        try:
            sandbox = await AsyncSandbox.connect(sandbox_id, api_key=self._api_key)
            result = await sandbox.commands.run(command, timeout=float(timeout))
        except TimeoutError as exc:
            raise SandboxTimeoutError(f"[E2B] Shell 执行超时（{timeout}s）") from exc
        except Exception as exc:
            raise SandboxUnavailableError(f"[E2B] execute_shell 失败: {exc}") from exc

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return ExecResult(
            stdout=result.stdout or "",
            stderr=result.stderr or "",
            exit_code=result.exit_code or 0,
            duration_ms=elapsed_ms,
        )

    async def files_read(self, sandbox_id: str, path: str) -> str:
        AsyncSandbox = self._sdk()
        self._assert_alive(sandbox_id)
        sandbox = await AsyncSandbox.connect(sandbox_id, api_key=self._api_key)
        content = await sandbox.files.read(path)
        return content if isinstance(content, str) else content.decode()

    async def files_write(self, sandbox_id: str, path: str, content: str) -> None:
        AsyncSandbox = self._sdk()
        self._assert_alive(sandbox_id)
        sandbox = await AsyncSandbox.connect(sandbox_id, api_key=self._api_key)
        await sandbox.files.write(path, content)

    async def connect(self, sandbox_id: str, timeout: int = 0) -> ConnectInfo:
        meta = _E2B_REGISTRY.get(sandbox_id, {})
        return ConnectInfo(
            sandbox_id=sandbox_id,
            host="",
            port=0,
            template_id=meta.get("template_id", ""),
        )

    async def get_logs(self, sandbox_id: str) -> str:
        return ""

    async def pause(self, sandbox_id: str) -> None:
        # E2B 云服务无 pause 接口，仅在本地注册表标记状态
        if sandbox_id in _E2B_REGISTRY:
            _E2B_REGISTRY[sandbox_id]["state"] = SandboxState.PAUSED

    async def resume(self, sandbox_id: str, timeout: int = 0) -> ConnectInfo:
        if sandbox_id not in _E2B_REGISTRY:
            raise SandboxDestroyedError(f"[E2B] 沙箱不存在: {sandbox_id}")
        _E2B_REGISTRY[sandbox_id]["state"] = SandboxState.RUNNING
        return await self.connect(sandbox_id)

    async def destroy(self, sandbox_id: str) -> None:
        AsyncSandbox = self._sdk()
        try:
            sandbox = await AsyncSandbox.connect(sandbox_id, api_key=self._api_key)
            await sandbox.kill()
        except Exception as exc:
            logger.warning("[E2B] destroy 失败（可能已销毁）: %s", exc)
        _E2B_REGISTRY.pop(sandbox_id, None)
        logger.info("[E2B] destroyed sandbox_id=%s", sandbox_id)

    # ── 内部辅助 ─────────────────────────────────────────────────────────────

    def _assert_alive(self, sandbox_id: str) -> None:
        if sandbox_id not in _E2B_REGISTRY:
            raise SandboxDestroyedError(f"[E2B] 沙箱不存在或已销毁: {sandbox_id}")
        if _E2B_REGISTRY[sandbox_id].get("state") == SandboxState.PAUSED:
            raise SandboxDestroyedError(f"[E2B] 沙箱已暂停，请先 resume: {sandbox_id}")
