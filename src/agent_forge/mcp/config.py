"""AgentForge MCP 客户端层

将 MCP Server 的 tools 无缝接入 SkillRegistry，
让 LLM 像调用内置 Skill 一样调用 MCP Server 提供的工具。

架构位置：
  Harness Executor → SkillDispatcher → MCPClientPool（本模块）→ MCP Server

支持两种 Server 启动模式：
  1. stdio：本地进程（npx / uvx / python 命令），适用于 @modelcontextprotocol/* 官方 Server
  2. sse：远程 HTTP Server，适用于云端 MCP 服务

配置示例（写入 .env 或 agent 的 mcp_config 字段）：
  MCP_SERVERS='{"filesystem": {"type": "stdio", "command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]}, "fetch": {"type": "stdio", "command": "uvx", "args": ["mcp-server-fetch"]}}'
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

from agent_forge.skills.runtime_spec import normalize_permissions

logger = logging.getLogger(__name__)

DEFAULT_UNDECLARED_MCP_PERMISSIONS = ["credential"]


# ── 配置数据类 ───────────────────────────────────────────────


@dataclass
class MCPServerConfig:
    """单个 MCP Server 的连接配置"""

    name: str
    server_type: str  # "stdio" | "sse"

    # stdio 模式
    command: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)

    # sse 模式
    url: str = ""
    headers: dict[str, str] = field(default_factory=dict)

    # MCP Server 能力边界。未声明时按未知高风险处理，避免第三方工具绕过 SkillPolicy。
    permissions: list[str] = field(default_factory=lambda: DEFAULT_UNDECLARED_MCP_PERMISSIONS.copy())

    def __post_init__(self) -> None:
        raw_permissions = self.permissions or DEFAULT_UNDECLARED_MCP_PERMISSIONS
        self.permissions = normalize_permissions(list(raw_permissions))

    @classmethod
    def from_dict(cls, name: str, data: dict) -> "MCPServerConfig":
        server_type = data.get("type", "stdio")
        return cls(
            name=name,
            server_type=server_type,
            command=data.get("command", ""),
            args=data.get("args", []),
            env=data.get("env", {}),
            url=data.get("url", ""),
            headers=data.get("headers", {}),
            permissions=data.get("permissions") or DEFAULT_UNDECLARED_MCP_PERMISSIONS,
        )


def load_mcp_configs() -> list[MCPServerConfig]:
    """从环境变量 MCP_SERVERS（JSON）加载所有 MCP Server 配置"""
    raw = os.getenv("MCP_SERVERS", "")
    if not raw:
        return []
    try:
        data: dict = json.loads(raw)
        configs = [MCPServerConfig.from_dict(name, cfg) for name, cfg in data.items()]
        logger.info("Loaded %d MCP server config(s): %s", len(configs), [c.name for c in configs])
        return configs
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.warning("Failed to parse MCP_SERVERS env var: %s", e)
        return []
