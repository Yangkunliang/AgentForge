"""
agent_forge.sandbox.cubesandbox
================================
CubeSandbox 执行器子包。

提供两种对接路径：
- e2b.py   CubeSandboxE2BExecutor（E2B SDK，推荐）
- api.py   CubeSandboxAPIExecutor（REST API，精细控制）

详细设计见 docs/tech-design/INTEGRATION-CUBESANDBOX.md §3.1
"""

from agent_forge.sandbox.cubesandbox.api import CubeSandboxAPIExecutor
from agent_forge.sandbox.cubesandbox.e2b import CubeSandboxE2BExecutor

__all__ = ["CubeSandboxE2BExecutor", "CubeSandboxAPIExecutor"]
