"""
agent_forge.sandbox.base
========================
沙箱抽象层：Protocol 接口、数据类、异常定义。

所有具体执行器（DockerSandboxExecutor、CubeSandboxE2BExecutor、
CubeSandboxAPIExecutor 等）均实现此处的 SandboxExecutor Protocol。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable


# ─────────────────────────────────────────────────────────────────────────────
# 枚举 & 数据类
# ─────────────────────────────────────────────────────────────────────────────

class SandboxState(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    PAUSED    = "paused"
    DESTROYED = "destroyed"
    TIMEOUT   = "timeout"


@dataclass
class SandboxConfig:
    """沙箱创建配置。

    Attributes:
        template_id:        使用的沙箱模板 ID（CubeSandbox）或镜像名（Docker）
        timeout_seconds:    沙箱 TTL，超时后自动暂停/销毁，默认 5 分钟
        network_public:     是否允许公网出站访问
        memory_mb:          内存上限（MB）；Docker 强制执行，CubeSandbox 按模板规格
        writable_layer_gb:  可写层大小（GB）；仅在模板构建时生效，运行时不可更改
        exposed_ports:      沙箱对外暴露的端口列表
    """
    template_id: str = ""
    timeout_seconds: int = 300
    network_public: bool = True
    memory_mb: int = 512
    writable_layer_gb: int = 1
    exposed_ports: list[int] = field(default_factory=lambda: [49999, 49983])


@dataclass
class ExecResult:
    """代码 / Shell 命令执行结果。"""
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


@dataclass
class ConnectInfo:
    """沙箱连接信息。

    Attributes:
        sandbox_id:   沙箱唯一 ID
        host:         沙箱内部 IP 或 hostname（纯地址，不含端口）
        port:         沙箱对外暴露的主端口（独立字段，不与 host 合并为 host:port）
        template_id:  创建时使用的模板 ID
        state:        沙箱当前状态
        timeout_at:   Unix 时间戳；0 表示无 TTL 限制
    """
    sandbox_id: str
    host: str
    port: int
    template_id: str
    state: SandboxState = SandboxState.RUNNING
    timeout_at: int = 0

    @property
    def address(self) -> str:
        """返回 host:port 格式的地址字符串，供需要合并格式的场景使用。"""
        return f"{self.host}:{self.port}"

    @property
    def is_expired(self) -> bool:
        """判断沙箱是否已超过 TTL。"""
        return self.timeout_at > 0 and time.time() > self.timeout_at


# ─────────────────────────────────────────────────────────────────────────────
# SandboxExecutor Protocol
# ─────────────────────────────────────────────────────────────────────────────

@runtime_checkable
class SandboxExecutor(Protocol):
    """沙箱执行器统一接口。

    所有具体执行器必须实现此 Protocol。上层（SandboxManager、Skills、Agents）
    只依赖此接口，不感知底层是 Mock / Docker / CubeSandbox。

    实现约定
    --------
    - create()    幂等：重复调用创建新沙箱，不复用旧沙箱
    - destroy()   幂等：已销毁的沙箱再次调用不应抛出异常
    - execute()   超时时抛出 SandboxTimeoutError，不截断后台进程
    - connect()   用于续期 TTL；传 timeout=0 表示使用沙箱原有 TTL
    """

    async def create(self, config: SandboxConfig) -> ConnectInfo:
        """创建新沙箱，返回连接信息。"""
        ...

    async def execute(
        self, sandbox_id: str, code: str, timeout: int = 30
    ) -> ExecResult:
        """在沙箱中执行 Python 代码。"""
        ...

    async def execute_shell(
        self, sandbox_id: str, command: str, timeout: int = 30
    ) -> ExecResult:
        """在沙箱中执行 Shell 命令。"""
        ...

    async def files_read(self, sandbox_id: str, path: str) -> str:
        """读取沙箱内文件内容。"""
        ...

    async def files_write(
        self, sandbox_id: str, path: str, content: str
    ) -> None:
        """向沙箱内写入文件。"""
        ...

    async def connect(self, sandbox_id: str, timeout: int = 0) -> ConnectInfo:
        """获取或续期已有沙箱的连接信息。timeout=0 使用沙箱原有 TTL。"""
        ...

    async def get_logs(self, sandbox_id: str) -> str:
        """获取沙箱运行日志（stdout + stderr 合并流）。"""
        ...

    async def pause(self, sandbox_id: str) -> None:
        """暂停沙箱（释放 CPU，保留内存快照）。"""
        ...

    async def resume(
        self, sandbox_id: str, timeout: int = 0
    ) -> ConnectInfo:
        """恢复已暂停的沙箱。"""
        ...

    async def destroy(self, sandbox_id: str) -> None:
        """彻底销毁沙箱，释放全部资源。幂等。"""
        ...


# ─────────────────────────────────────────────────────────────────────────────
# 异常体系
# ─────────────────────────────────────────────────────────────────────────────

class SandboxError(Exception):
    """沙箱异常基类。"""


class SandboxUnavailableError(SandboxError):
    """沙箱服务不可达（网络故障、服务未启动等）。
    触发降级策略：自动切换到 DockerSandboxExecutor。
    """


class SandboxCreationError(SandboxError):
    """沙箱创建失败（资源不足、模板不存在等）。"""


class SandboxDestroyedError(SandboxError):
    """对已销毁沙箱发起操作。HTTP 层返回 410 Gone。"""


class SandboxTimeoutError(SandboxError):
    """代码 / Shell 执行超时。"""


class SandboxAcquireTimeoutError(SandboxError):
    """获取沙箱超时（semaphore 或 pool acquire 等待超过阈值）。"""


class SandboxAuthError(SandboxError):
    """API Key 无效或权限不足。不触发降级，直接返回 401。"""


class FileAccessDeniedError(SandboxError):
    """文件访问路径不在白名单内（路径穿越防护）。"""
