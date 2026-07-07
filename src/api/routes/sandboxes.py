"""沙箱 REST API 路由

提供沙箱的完整生命周期管理端点。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Path

from agent_forge.config import sandbox_settings
from agent_forge.sandbox.base import (
    ConnectInfo,
    ExecResult,
    SandboxAuthError,
    SandboxConfig,
    SandboxCreationError,
    SandboxDestroyedError,
    SandboxTimeoutError,
    SandboxUnavailableError,
)
from agent_forge.sandbox.factory import SandboxProviderFactory
from agent_forge.sandbox.manager import SandboxManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["沙箱执行层"])

# 全局 SandboxManager 单例（由 main.py lifespan 初始化）
_global_sandbox: SandboxManager | None = None


def _get_manager() -> SandboxManager:
    """获取全局 SandboxManager，未初始化时返回基于 mock 的 fallback。"""
    global _global_sandbox
    if _global_sandbox is None:
        executor = SandboxProviderFactory.create(
            provider=sandbox_settings.cube_sandbox_default_provider,
            url=sandbox_settings.cube_sandbox_url,
            api_key=sandbox_settings.cube_sandbox_api_key,
            template_id=sandbox_settings.cube_template_id,
        )
        _global_sandbox = SandboxManager(
            executor, ttl_seconds=sandbox_settings.cube_sandbox_timeout
        )
    return _global_sandbox


# ── 异常到 HTTP 状态码映射 ──────────────────────────────────────

def _error_to_http(e: Exception) -> tuple[int, dict]:
    """将沙箱异常映射为 HTTP 响应。"""
    if isinstance(e, SandboxAuthError):
        return 401, {"error": "auth", "detail": str(e)}
    if isinstance(e, SandboxDestroyedError):
        return 410, {"error": "destroyed", "detail": str(e)}
    if isinstance(e, SandboxTimeoutError):
        return 408, {"error": "timeout", "detail": str(e)}
    if isinstance(e, SandboxCreationError):
        return 409, {"error": "conflict", "detail": str(e)}
    if isinstance(e, SandboxUnavailableError):
        return 503, {"error": "unavailable", "detail": str(e)}
    return 500, {"error": "internal_error", "detail": str(e)}


# ── 端点 ───────────────────────────────────────────────────────

@router.post("")
async def create_sandbox(
    config: SandboxConfig | None = None,
) -> dict:
    """创建新沙箱。"""
    try:
        manager = _get_manager()
        sandbox_id = await manager.get_or_create()
        return {"sandbox_id": sandbox_id, "status": "running"}
    except Exception as e:
        status, body = _error_to_http(e)
        raise HTTPException(status_code=status, detail=body)


@router.post("/{sandbox_id}/execute")
async def execute_code(
    sandbox_id: str = Path(..., description="沙箱 ID"),
    code: str = "",
    timeout: int = 30,
) -> dict:
    """在沙箱中执行 Python 代码。"""
    try:
        manager = _get_manager()
        manager._sandbox_id = sandbox_id  # 切换到指定沙箱
        result: ExecResult = await manager.execute(code, timeout=timeout)
        return {
            "sandbox_id": sandbox_id,
            "success": True,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
            "duration_ms": result.duration_ms,
        }
    except Exception as e:
        status, body = _error_to_http(e)
        raise HTTPException(status_code=status, detail=body)


@router.post("/{sandbox_id}/files/read")
async def read_file(
    sandbox_id: str = Path(..., description="沙箱 ID"),
    body: dict = {},
) -> dict:
    """读取沙箱内文件。"""
    try:
        manager = _get_manager()
        manager._sandbox_id = sandbox_id
        path = body.get("path", "")
        content = await manager.files_read(path)
        return {"sandbox_id": sandbox_id, "path": path, "content": content}
    except Exception as e:
        status, body = _error_to_http(e)
        raise HTTPException(status_code=status, detail=body)


@router.post("/{sandbox_id}/files/write")
async def write_file(
    sandbox_id: str = Path(..., description="沙箱 ID"),
    body: dict = {},
) -> dict:
    """向沙箱内写入文件。"""
    try:
        manager = _get_manager()
        manager._sandbox_id = sandbox_id
        path = body.get("path", "")
        content = body.get("content", "")
        await manager.files_write(path, content)
        return {"sandbox_id": sandbox_id, "path": path, "success": True}
    except Exception as e:
        status, body = _error_to_http(e)
        raise HTTPException(status_code=status, detail=body)


@router.post("/{sandbox_id}/pause")
async def pause_sandbox(
    sandbox_id: str = Path(..., description="沙箱 ID"),
) -> dict:
    """暂停沙箱。"""
    try:
        manager = _get_manager()
        manager._sandbox_id = sandbox_id
        await manager._executor.pause(sandbox_id)
        return {"sandbox_id": sandbox_id, "status": "paused"}
    except Exception as e:
        status, body = _error_to_http(e)
        raise HTTPException(status_code=status, detail=body)


@router.post("/{sandbox_id}/resume")
async def resume_sandbox(
    sandbox_id: str = Path(..., description="沙箱 ID"),
) -> dict:
    """恢复已暂停的沙箱。"""
    try:
        manager = _get_manager()
        manager._sandbox_id = sandbox_id
        info: ConnectInfo = await manager._executor.resume(sandbox_id)
        return {
            "sandbox_id": sandbox_id,
            "status": "running",
            "host": info.host,
            "port": info.port,
        }
    except Exception as e:
        status, body = _error_to_http(e)
        raise HTTPException(status_code=status, detail=body)


@router.post("/{sandbox_id}/destroy")
async def destroy_sandbox(
    sandbox_id: str = Path(..., description="沙箱 ID"),
) -> dict:
    """彻底销毁沙箱。"""
    try:
        manager = _get_manager()
        manager._sandbox_id = sandbox_id
        await manager.destroy()
        return {"sandbox_id": sandbox_id, "status": "destroyed"}
    except Exception as e:
        status, body = _error_to_http(e)
        raise HTTPException(status_code=status, detail=body)


@router.get("")
async def list_sandboxes() -> dict:
    """列出当前所有活跃沙箱（返回 manager 持有的 sandbox_id）。"""
    try:
        manager = _get_manager()
        sandbox_id = manager.sandbox_id
        return {
            "sandboxes": [
                {"sandbox_id": sandbox_id, "status": "running"}
            ]
            if sandbox_id
            else [],
        }
    except Exception as e:
        status, body = _error_to_http(e)
        raise HTTPException(status_code=status, detail=body)
