"""MCPClientPool — MCP Server 连接池与工具调用路由

职责：
  1. 按 MCPServerConfig 启动并持有 MCP ClientSession
  2. 将每个 Server 暴露的 tools 转换为 OpenAI tool 定义，注册到 SkillRegistry
  3. 根据 tool_name 路由调用到正确的 Server，并返回 JSON 结果

依赖：
  pip install mcp  （MCP Python SDK，Anthropic 官方）

若 `mcp` 未安装，模块优雅降级：warn 后跳过，不影响内置 Skill 功能。
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from agent_forge.mcp.config import MCPServerConfig

logger = logging.getLogger(__name__)

# ── MCP SDK 导入（可选依赖）────────────────────────────────


def _import_mcp():
    """惰性导入 mcp SDK，未安装时返回 None"""
    try:
        import mcp
        return mcp
    except ImportError:
        return None


# ── 单个 Server 客户端 ────────────────────────────────────


class MCPServerClient:
    """封装与单个 MCP Server 的生命周期和工具调用"""

    def __init__(self, config: MCPServerConfig) -> None:
        self.config = config
        self._session: Any = None   # mcp.ClientSession
        self._tools: list[dict] = []  # OpenAI tool 格式
        self._tool_names: set[str] = set()
        self._ready = asyncio.Event()

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def tools(self) -> list[dict]:
        """该 Server 提供的 OpenAI tool 定义列表"""
        return self._tools

    async def start(self) -> bool:
        """启动 Server 连接，拉取工具列表。返回是否成功。"""
        mcp = _import_mcp()
        if mcp is None:
            logger.warning(
                "MCP SDK not installed. Run: pip install mcp  "
                "Server '%s' will be skipped.", self.config.name
            )
            return False

        try:
            if self.config.server_type == "stdio":
                return await self._start_stdio(mcp)
            elif self.config.server_type == "sse":
                return await self._start_sse(mcp)
            else:
                logger.error("Unknown MCP server type: %s", self.config.server_type)
                return False
        except Exception as e:
            logger.error("Failed to start MCP server '%s': %s", self.config.name, e)
            return False

    async def _start_stdio(self, mcp: Any) -> bool:
        """启动 stdio 模式的 MCP Server（本地进程）"""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        env = {**dict(__import__("os").environ), **self.config.env}

        server_params = StdioServerParameters(
            command=self.config.command,
            args=self.config.args,
            env=env,
        )

        # stdio_client 返回上下文管理器，需要在整个生命周期保持连接
        # 此处用 asyncio.Task 持有，连接断开时自动重连（后续可扩展）
        self._stdio_ctx = stdio_client(server_params)
        read, write = await self._stdio_ctx.__aenter__()

        self._session_ctx = ClientSession(read, write)
        self._session = await self._session_ctx.__aenter__()
        await self._session.initialize()

        await self._fetch_tools()
        self._ready.set()
        logger.info(
            "MCP server '%s' (stdio) started, %d tools: %s",
            self.config.name, len(self._tools),
            [t["function"]["name"] for t in self._tools],
        )
        return True

    async def _start_sse(self, mcp: Any) -> bool:
        """启动 SSE 模式的 MCP Server（远程 HTTP）"""
        from mcp import ClientSession
        from mcp.client.sse import sse_client

        self._sse_ctx = sse_client(
            url=self.config.url,
            headers=self.config.headers,
        )
        read, write = await self._sse_ctx.__aenter__()

        self._session_ctx = ClientSession(read, write)
        self._session = await self._session_ctx.__aenter__()
        await self._session.initialize()

        await self._fetch_tools()
        self._ready.set()
        logger.info(
            "MCP server '%s' (sse) started, %d tools: %s",
            self.config.name, len(self._tools),
            [t["function"]["name"] for t in self._tools],
        )
        return True

    async def _fetch_tools(self) -> None:
        """拉取 Server 工具列表并转换为 OpenAI tool 格式"""
        result = await self._session.list_tools()
        self._tools = []
        self._tool_names = set()

        for tool in result.tools:
            # MCP Tool → OpenAI Function Calling 格式
            openai_tool = {
                "type": "function",
                "function": {
                    "name": f"mcp__{self.config.name}__{tool.name}",
                    "description": (tool.description or f"{self.config.name} tool: {tool.name}"),
                    "parameters": tool.inputSchema if tool.inputSchema else {
                        "type": "object",
                        "properties": {},
                    },
                },
                # 元数据，供 Dispatcher 路由使用
                "_mcp_server": self.config.name,
                "_mcp_tool": tool.name,
            }
            self._tools.append(openai_tool)
            self._tool_names.add(f"mcp__{self.config.name}__{tool.name}")

    async def call_tool(self, mcp_tool_name: str, arguments: dict[str, Any]) -> str:
        """
        调用 MCP Server 的一个工具。

        Args:
            mcp_tool_name: 原始工具名（不含前缀），如 "read_file"
            arguments: 工具参数 dict

        Returns:
            JSON 字符串，供 LLM tool role message 使用
        """
        if self._session is None:
            return json.dumps({"error": f"MCP server '{self.config.name}' not connected"})

        try:
            result = await self._session.call_tool(mcp_tool_name, arguments)

            # MCP CallToolResult.content 是 list of ContentBlock
            # 统一转为字符串
            parts: list[str] = []
            for block in result.content:
                if hasattr(block, "text"):
                    parts.append(block.text)
                elif hasattr(block, "data"):
                    parts.append(f"[binary data, {len(block.data)} bytes]")
                else:
                    parts.append(str(block))

            combined = "\n".join(parts) if parts else "(empty result)"

            # 尝试保留 JSON 结构
            if len(parts) == 1:
                try:
                    parsed = json.loads(parts[0])
                    return json.dumps(parsed, ensure_ascii=False)
                except (json.JSONDecodeError, TypeError):
                    pass

            return json.dumps({"result": combined}, ensure_ascii=False)

        except Exception as e:
            logger.exception("MCP tool call failed: %s/%s → %s", self.config.name, mcp_tool_name, e)
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    async def stop(self) -> None:
        """关闭连接"""
        try:
            if hasattr(self, "_session_ctx") and self._session_ctx:
                await self._session_ctx.__aexit__(None, None, None)
            if hasattr(self, "_stdio_ctx") and self._stdio_ctx:
                await self._stdio_ctx.__aexit__(None, None, None)
            if hasattr(self, "_sse_ctx") and self._sse_ctx:
                await self._sse_ctx.__aexit__(None, None, None)
        except Exception as e:
            logger.debug("MCP server '%s' stop error (ignored): %s", self.config.name, e)


# ── 连接池 ────────────────────────────────────────────────


class MCPClientPool:
    """管理所有 MCP Server 客户端的生命周期，并作为工具调用路由"""

    def __init__(self) -> None:
        self._clients: dict[str, MCPServerClient] = {}
        # tool function name（带前缀） → client
        self._tool_map: dict[str, MCPServerClient] = {}

    async def start_all(self, configs: list[MCPServerConfig]) -> None:
        """启动所有配置的 MCP Server，成功的注册到 SkillRegistry"""
        if not configs:
            logger.info("No MCP servers configured, skipping")
            return

        results = await asyncio.gather(
            *[self._start_one(cfg) for cfg in configs],
            return_exceptions=True,
        )

        ok_count = sum(1 for r in results if r is True)
        logger.info("MCPClientPool: %d/%d servers started", ok_count, len(configs))

        # 将成功启动的 Server 工具注册到 SkillRegistry
        self._register_to_skill_registry()

    async def _start_one(self, config: MCPServerConfig) -> bool:
        client = MCPServerClient(config)
        ok = await client.start()
        if ok:
            self._clients[config.name] = client
            for tool in client.tools:
                self._tool_map[tool["function"]["name"]] = client
        return ok

    def _register_to_skill_registry(self) -> None:
        """将所有 MCP tools 注册到全局 SkillRegistry"""
        from agent_forge.skills.registry import get_skill_registry
        registry = get_skill_registry()

        for server_name, client in self._clients.items():
            if not client.tools:
                continue

            # 构建 executors dict（工具名 → 异步调用函数）
            executors: dict[str, Any] = {}
            for tool_def in client.tools:
                fn_name = tool_def["function"]["name"]  # e.g. mcp__filesystem__read_file
                mcp_tool = tool_def["_mcp_tool"]         # e.g. read_file
                client_ref = client

                # 用默认参数捕获 mcp_tool 和 client_ref
                async def make_executor(mcp_tool_name: str, mcp_client: MCPServerClient):
                    async def executor(**kwargs: Any) -> str:
                        return await mcp_client.call_tool(mcp_tool_name, kwargs)
                    return executor

                # Python 闭包捕获需要立即求值，用 Task 方式
                executors[fn_name] = _make_mcp_executor(client, mcp_tool)

            # 注册（tool_defs 去掉内部 _mcp_* 字段再注入 LLM）
            clean_tool_defs = [
                {k: v for k, v in t.items() if not k.startswith("_")}
                for t in client.tools
            ]
            registry.register(
                skill_name=f"mcp_{server_name}",
                tool_defs=clean_tool_defs,
                executors=executors,
            )
            logger.info(
                "Registered MCP server '%s' with %d tools",
                server_name, len(clean_tool_defs),
            )

    async def call_tool(self, tool_fn_name: str, arguments: dict[str, Any]) -> str:
        """根据 tool function name 路由到对应 MCP Server 执行"""
        client = self._tool_map.get(tool_fn_name)
        if client is None:
            return json.dumps({"error": f"No MCP server found for tool '{tool_fn_name}'"})

        # tool_fn_name = mcp__<server>__<tool>
        parts = tool_fn_name.split("__", 2)
        mcp_tool_name = parts[2] if len(parts) == 3 else tool_fn_name
        return await client.call_tool(mcp_tool_name, arguments)

    async def stop_all(self) -> None:
        """关闭所有连接（应用关闭时调用）"""
        await asyncio.gather(
            *[c.stop() for c in self._clients.values()],
            return_exceptions=True,
        )
        self._clients.clear()
        self._tool_map.clear()
        logger.info("MCPClientPool: all servers stopped")

    @property
    def active_servers(self) -> list[str]:
        return list(self._clients.keys())

    @property
    def all_tool_defs(self) -> list[dict]:
        result: list[dict] = []
        for client in self._clients.values():
            result.extend(
                {k: v for k, v in t.items() if not k.startswith("_")}
                for t in client.tools
            )
        return result


def _make_mcp_executor(client: MCPServerClient, mcp_tool_name: str):
    """工厂函数：创建 MCP 工具的 async executor，正确捕获闭包变量"""
    async def executor(**kwargs: Any) -> str:
        return await client.call_tool(mcp_tool_name, kwargs)
    return executor


# ── 全局单例 ──────────────────────────────────────────────


_pool: MCPClientPool | None = None


def get_mcp_pool() -> MCPClientPool:
    global _pool
    if _pool is None:
        _pool = MCPClientPool()
    return _pool
