"""MCP Client 单元测试"""

from __future__ import annotations

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from agent_forge.mcp.config import MCPServerConfig, load_mcp_configs
from agent_forge.mcp.client import MCPServerClient, MCPClientPool, get_mcp_pool


class TestMCPServerConfig:
    """MCP Server 配置测试"""

    def test_from_dict_stdio(self):
        data = {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem"],
            "env": {"API_KEY": "test"},
        }
        config = MCPServerConfig.from_dict("filesystem", data)
        assert config.name == "filesystem"
        assert config.server_type == "stdio"
        assert config.command == "npx"
        assert config.args == ["-y", "@modelcontextprotocol/server-filesystem"]
        assert config.env == {"API_KEY": "test"}

    def test_from_dict_sse(self):
        data = {
            "type": "sse",
            "url": "https://mcp.example.com",
            "headers": {"Authorization": "Bearer token"},
        }
        config = MCPServerConfig.from_dict("remote", data)
        assert config.name == "remote"
        assert config.server_type == "sse"
        assert config.url == "https://mcp.example.com"
        assert config.headers == {"Authorization": "Bearer token"}

    def test_from_dict_default_type(self):
        data = {"command": "echo", "args": ["hello"]}
        config = MCPServerConfig.from_dict("test", data)
        assert config.server_type == "stdio"


class TestMCPConfigLoader:
    """MCP 配置加载测试"""

    @patch("agent_forge.mcp.config.os.getenv", return_value="")
    def test_no_config(self, mock_env):
        configs = load_mcp_configs()
        assert configs == []

    @patch("agent_forge.mcp.config.os.getenv", return_value='{"filesystem": {"type": "stdio", "command": "npx"}}')
    def test_valid_config(self, mock_env):
        configs = load_mcp_configs()
        assert len(configs) == 1
        assert configs[0].name == "filesystem"

    @patch("agent_forge.mcp.config.os.getenv", return_value='invalid json')
    def test_invalid_json(self, mock_env):
        configs = load_mcp_configs()
        assert configs == []


@pytest.mark.asyncio
class TestMCPServerClient:
    """MCP Server 客户端测试"""

    async def test_client_initialization(self):
        config = MCPServerConfig(
            name="test-server",
            server_type="stdio",
            command="echo",
            args=["hello"],
        )
        client = MCPServerClient(config)
        assert client.name == "test-server"
        assert client.tools == []

    @patch("agent_forge.mcp.client._import_mcp", return_value=None)
    async def test_start_without_mcp_sdk(self, mock_import):
        config = MCPServerConfig(name="test", server_type="stdio", command="echo")
        client = MCPServerClient(config)
        result = await client.start()
        assert result is False

    async def test_call_tool_not_ready(self):
        config = MCPServerConfig(name="test", server_type="stdio", command="echo")
        client = MCPServerClient(config)
        result = await client.call_tool("test_tool", {"arg": "value"})
        assert '"error"' in result


@pytest.mark.asyncio
class TestMCPClientPool:
    """MCP 客户端连接池测试"""

    async def test_pool_initialization(self):
        pool = MCPClientPool()
        assert pool.active_servers == []
        assert pool.all_tool_defs == []

    @patch("agent_forge.mcp.client._import_mcp", return_value=None)
    async def test_start_all_without_sdk(self, mock_import):
        pool = MCPClientPool()
        configs = [
            MCPServerConfig(name="test", server_type="stdio", command="echo"),
        ]
        await pool.start_all(configs)
        assert pool.active_servers == []

    async def test_call_tool_not_found(self):
        pool = MCPClientPool()
        result = await pool.call_tool("nonexistent_tool", {})
        assert '"error"' in result

    async def test_stop_all_empty(self):
        pool = MCPClientPool()
        await pool.stop_all()
        assert pool.active_servers == []


class TestMCPClientPoolSingleton:
    """MCP 客户端连接池单例测试"""

    def test_get_mcp_pool_singleton(self):
        pool1 = get_mcp_pool()
        pool2 = get_mcp_pool()
        assert pool1 is pool2