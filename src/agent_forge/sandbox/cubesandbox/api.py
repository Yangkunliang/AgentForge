"""
agent_forge.sandbox.cubesandbox.api
=====================================
CubeSandboxAPIExecutor：基于 CubeSandbox REST API 的执行器。

适用于需要精细控制的场景：
- 自定义快照管理
- 集群调度策略
- 不想引入 E2B SDK 依赖

依赖
----
httpx（已在 AgentForge 依赖中）

API 参考
--------
docs/tech-design/INTEGRATION-CUBESANDBOX.md §3.1 路径 B
"""

from __future__ import annotations

import logging
import time
import uuid

import httpx

from agent_forge.sandbox.base import (
    ConnectInfo,
    ExecResult,
    SandboxAuthError,
    SandboxConfig,
    SandboxCreationError,
    SandboxDestroyedError,
    SandboxState,
    SandboxTimeoutError,
    SandboxUnavailableError,
)

logger = logging.getLogger(__name__)

_API_REGISTRY: dict[str, dict] = {}


class CubeSandboxAPIExecutor:
    """基于 CubeSandbox REST API 的执行器。

    Args:
        base_url:  CubeSandbox API 根地址（如 http://127.0.0.1:3000）
        api_key:   Bearer Token，对应 CUBE_SANDBOX_API_KEY
    """

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(30.0, connect=5.0),
        )

    # ── Protocol 实现 ─────────────────────────────────────────────────────────

    async def create(self, config: SandboxConfig) -> ConnectInfo:
        try:
            resp = await self._client.post("/sandboxes", json={
                "templateID": config.template_id,
                "timeout": config.timeout_seconds,
            })
        except httpx.ConnectError as e:
            raise SandboxUnavailableError(
                f"CubeSandbox API 不可达（{self._base_url}）: {e}"
            ) from e

        self._raise_for_status(resp)
        data = resp.json()

        sandbox_id = data["sandboxID"]
        _API_REGISTRY[sandbox_id] = {
            "state": SandboxState.RUNNING,
            "template_id": config.template_id,
            "created_at": time.time(),
            "host": data.get("host", "127.0.0.1"),
            "port": data.get("port", 49999),
        }
        logger.info("[CubeSandbox/API] created sandbox_id=%s", sandbox_id)
        return ConnectInfo(
            sandbox_id=sandbox_id,
            host=data.get("host", "127.0.0.1"),
            port=data.get("port", 49999),
            template_id=config.template_id,
        )

    async def execute(
        self, sandbox_id: str, code: str, timeout: int = 30
    ) -> ExecResult:
        start = time.monotonic()
        try:
            resp = await self._client.post(
                f"/sandboxes/{sandbox_id}/code",
                json={"code": code, "timeout": timeout},
            )
        except httpx.ConnectError as e:
            raise SandboxUnavailableError(f"CubeSandbox API 不可达: {e}") from e

        self._raise_for_status(resp)
        data = resp.json()

        if data.get("timedOut"):
            raise SandboxTimeoutError(
                f"[CubeSandbox/API] 代码执行超时（{timeout}s）"
            )

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return ExecResult(
            stdout=data.get("stdout", ""),
            stderr=data.get("stderr", ""),
            exit_code=data.get("exitCode", 0),
            duration_ms=data.get("durationMs", elapsed_ms),
        )

    async def execute_shell(
        self, sandbox_id: str, command: str, timeout: int = 30
    ) -> ExecResult:
        start = time.monotonic()
        try:
            resp = await self._client.post(
                f"/sandboxes/{sandbox_id}/shell",
                json={"command": command, "timeout": timeout},
            )
        except httpx.ConnectError as e:
            raise SandboxUnavailableError(f"CubeSandbox API 不可达: {e}") from e

        self._raise_for_status(resp)
        data = resp.json()

        if data.get("timedOut"):
            raise SandboxTimeoutError(
                f"[CubeSandbox/API] Shell 执行超时（{timeout}s）"
            )

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return ExecResult(
            stdout=data.get("stdout", ""),
            stderr=data.get("stderr", ""),
            exit_code=data.get("exitCode", 0),
            duration_ms=data.get("durationMs", elapsed_ms),
        )

    async def files_read(self, sandbox_id: str, path: str) -> str:
        resp = await self._client.post(
            f"/sandboxes/{sandbox_id}/files/read",
            json={"path": path},
        )
        self._raise_for_status(resp)
        return resp.json().get("content", "")

    async def files_write(
        self, sandbox_id: str, path: str, content: str
    ) -> None:
        resp = await self._client.post(
            f"/sandboxes/{sandbox_id}/files/write",
            json={"path": path, "content": content},
        )
        self._raise_for_status(resp)

    async def connect(self, sandbox_id: str, timeout: int = 0) -> ConnectInfo:
        resp = await self._client.post(
            f"/sandboxes/{sandbox_id}/connect",
            json={"timeout": timeout},
        )
        self._raise_for_status(resp)
        data = resp.json()
        meta = _API_REGISTRY.get(sandbox_id, {})
        return ConnectInfo(
            sandbox_id=sandbox_id,
            host=data.get("host", meta.get("host", "127.0.0.1")),
            port=data.get("port", meta.get("port", 49999)),
            template_id=meta.get("template_id", ""),
        )

    async def get_logs(self, sandbox_id: str) -> str:
        resp = await self._client.get(f"/sandboxes/{sandbox_id}/logs")
        self._raise_for_status(resp)
        return resp.json().get("logs", "")

    async def pause(self, sandbox_id: str) -> None:
        resp = await self._client.post(f"/sandboxes/{sandbox_id}/pause")
        self._raise_for_status(resp)
        if sandbox_id in _API_REGISTRY:
            _API_REGISTRY[sandbox_id]["state"] = SandboxState.PAUSED
        logger.info("[CubeSandbox/API] paused sandbox_id=%s", sandbox_id)

    async def resume(self, sandbox_id: str, timeout: int = 0) -> ConnectInfo:
        resp = await self._client.post(
            f"/sandboxes/{sandbox_id}/resume",
            json={"timeout": timeout},
        )
        self._raise_for_status(resp)
        if sandbox_id in _API_REGISTRY:
            _API_REGISTRY[sandbox_id]["state"] = SandboxState.RUNNING
        return await self.connect(sandbox_id)

    async def destroy(self, sandbox_id: str) -> None:
        try:
            resp = await self._client.delete(f"/sandboxes/{sandbox_id}")
            if resp.status_code not in (200, 204, 404):
                logger.warning(
                    "[CubeSandbox/API] destroy 返回非预期状态码: %d", resp.status_code
                )
        except Exception as e:
            logger.warning("[CubeSandbox/API] destroy 失败（可能已销毁）: %s", e)
        _API_REGISTRY.pop(sandbox_id, None)
        logger.info("[CubeSandbox/API] destroyed sandbox_id=%s", sandbox_id)

    async def close(self) -> None:
        """关闭 HTTP 客户端，应在应用关闭时调用。"""
        await self._client.aclose()

    # ── 内部辅助 ─────────────────────────────────────────────────────────────

    def _raise_for_status(self, resp: httpx.Response) -> None:
        """将 HTTP 错误码映射为沙箱异常。"""
        if resp.status_code == 401:
            raise SandboxAuthError(
                f"CubeSandbox API Key 无效（401）: {self._base_url}"
            )
        if resp.status_code == 404:
            raise SandboxDestroyedError(
                f"沙箱不存在或已销毁（404）: {resp.url}"
            )
        if resp.status_code == 409:
            raise SandboxCreationError(
                f"沙箱创建冲突（409）: {resp.text[:200]}"
            )
        if resp.status_code >= 500:
            raise SandboxUnavailableError(
                f"CubeSandbox 服务错误（{resp.status_code}）: {resp.text[:200]}"
            )
        if not resp.is_success:
            raise SandboxUnavailableError(
                f"CubeSandbox API 请求失败（{resp.status_code}）: {resp.text[:200]}"
            )
