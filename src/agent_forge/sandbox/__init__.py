"""
agent_forge.sandbox
===================
沙箱执行层：为 LLM 生成的代码提供隔离的执行环境。

包结构
------
sandbox/
├── __init__.py          ← 公共 API 导出（本文件）
├── base.py              ← Protocol 接口、数据类、异常定义
├── manager.py           ← SandboxManager（生命周期 + TTL 管理）
├── pool.py              ← SandboxPool（热沙箱池，可选优化）
├── mock.py              ← MockSandboxExecutor（本地开发 / 单元测试用）
├── docker.py            ← DockerSandboxExecutor（可信代码，容器级隔离）
└── cubesandbox/
    ├── __init__.py
    ├── e2b.py           ← CubeSandboxE2BExecutor（E2B SDK，推荐）
    └── api.py           ← CubeSandboxAPIExecutor（REST API，精细控制）

隔离级别速查
-----------
MockSandboxExecutor    → ❌ 无隔离（仅开发测试）
DockerSandboxExecutor  → ⚠️  Namespace+Cgroup（可信代码）
CubeSandboxExecutor    → ✅ KVM 内核级隔离（LLM 生成的不可信代码）

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
from agent_forge.sandbox.mock import MockSandboxExecutor
from agent_forge.sandbox.pool import SandboxPool

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
    # 执行器（开箱即用）
    "MockSandboxExecutor",
]
