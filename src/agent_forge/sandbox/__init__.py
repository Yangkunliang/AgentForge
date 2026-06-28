"""
agent_forge.sandbox
===================
沙箱执行层：为 LLM 生成的代码提供 KVM 级隔离的执行环境。

包结构
------
sandbox/
├── __init__.py          ← 公共 API 导出（本文件）
├── base.py              ← Protocol 接口、数据类、异常定义
├── manager.py           ← SandboxManager（生命周期 + TTL 管理）
├── pool.py              ← SandboxPool（热沙箱池，可选优化）
├── reclaimer.py         ← SandboxReclaimer（TTL 后台扫描 + 自动回收）
├── factory.py           ← SandboxProviderFactory（按配置创建 Executor）
└── cubesandbox/
    ├── __init__.py
    ├── e2b.py           ← CubeSandboxE2BExecutor（E2B SDK v1，推荐）
    └── api.py           ← CubeSandboxAPIExecutor（REST API，精细控制）

隔离级别
--------
CubeSandboxE2BExecutor  → ✅ KVM 内核级隔离（E2B 云 或 自部署 CubeSandbox）
CubeSandboxAPIExecutor  → ✅ KVM 内核级隔离（自部署 CubeSandbox REST API）

不再维护的执行器
---------------
MockSandboxExecutor  —— 已删除，开发环境直接用 E2B 云（配置 E2B_API_KEY）
DockerSandboxExecutor —— 已删除，KVM 隔离已覆盖 Docker 的所有场景

详细设计见 docs/tech-design/INTEGRATION-CUBESANDBOX.md
"""

from agent_forge.sandbox.base import (
    ConnectInfo,
    ExecResult,
    FileAccessDeniedError,
    SandboxAuthError,
    SandboxConfig,
    SandboxCreationError,
    SandboxDestroyedError,
    SandboxError,
    SandboxExecutor,
    SandboxState,
    SandboxTimeoutError,
    SandboxUnavailableError,
)
from agent_forge.sandbox.manager import SandboxManager
from agent_forge.sandbox.pool import SandboxPool
from agent_forge.sandbox.reclaimer import SandboxReclaimer
from agent_forge.sandbox.factory import SandboxProviderFactory

__all__ = [
    # 数据类 & 协议
    "SandboxExecutor",
    "SandboxConfig",
    "SandboxState",
    "ConnectInfo",
    "ExecResult",
    # 异常
    "SandboxError",
    "SandboxAuthError",
    "SandboxCreationError",
    "SandboxDestroyedError",
    "SandboxTimeoutError",
    "SandboxUnavailableError",
    "FileAccessDeniedError",
    # 核心组件
    "SandboxManager",
    "SandboxPool",
    "SandboxReclaimer",
    # 工厂
    "SandboxProviderFactory",
]
