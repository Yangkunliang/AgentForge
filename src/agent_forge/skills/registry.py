"""SkillRegistry — 运行时 Skill 注册表

缓存 Skill 的 tool 定义和执行函数，避免每次请求都查 DB。
内置 Skill 在 startup 时通过 register_builtin() 直接注册。
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Awaitable
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class SkillRegistry:
    """单例运行时注册表"""

    _instance: "SkillRegistry | None" = None

    def __init__(self) -> None:
        # skill_name → [OpenAI tool def dict]
        self._tool_defs: dict[str, list[dict]] = {}
        # tool function name → async callable
        self._executors: dict[str, Callable[..., Awaitable[Any]]] = {}

    @classmethod
    def get_instance(cls) -> "SkillRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── 注册 ────────────────────────────────────────────────

    def register(
        self,
        skill_name: str,
        tool_defs: list[dict],
        executors: dict[str, Callable[..., Awaitable[Any]]],
    ) -> None:
        """注册一个 Skill 的 tool 定义和执行函数。

        Args:
            skill_name:  Skill 名称（对应 DB skills.name）
            tool_defs:   该 Skill 的 OpenAI tool 定义列表
            executors:   {function_name: async_callable} 映射
        """
        self._tool_defs[skill_name] = tool_defs
        self._executors.update(executors)
        logger.info(
            "SkillRegistry: registered '%s' with tools=%s",
            skill_name,
            [t["function"]["name"] for t in tool_defs],
        )

    def unregister(self, skill_name: str) -> None:
        """卸载 Skill（安装/卸载后调用）"""
        tool_defs = self._tool_defs.pop(skill_name, [])
        for td in tool_defs:
            self._executors.pop(td["function"]["name"], None)
        logger.info("SkillRegistry: unregistered '%s'", skill_name)

    # ── 查询 ────────────────────────────────────────────────

    def get_all_tool_defs(self) -> list[dict]:
        """获取所有已注册的 tool 定义列表（直接注入 LLM tools 参数）"""
        result: list[dict] = []
        for defs in self._tool_defs.values():
            result.extend(defs)
        return result

    async def get_enabled_tool_defs(self, db: AsyncSession) -> list[dict]:
        """从 DB 过滤 enabled=True 的 Skill，返回其 tool 定义。

        内置 Skill 不在 DB 里（或通过 builtin.py 注册）时退化为全量返回。
        """
        from agent_forge.models.skill import Skill

        try:
            result = await db.execute(select(Skill).where(Skill.enabled == True))  # noqa: E712
            enabled_names = {s.name for s in result.scalars().all()}

            if not enabled_names:
                # DB 里没有任何记录（e.g. 测试环境），返回全部
                return self.get_all_tool_defs()

            tool_defs: list[dict] = []
            for skill_name, defs in self._tool_defs.items():
                if skill_name in enabled_names:
                    tool_defs.extend(defs)
            return tool_defs
        except Exception as e:
            logger.warning("Failed to filter enabled skills from DB, using all: %s", e)
            return self.get_all_tool_defs()

    def get_executor(self, tool_function_name: str) -> Callable[..., Awaitable[Any]] | None:
        """根据 tool function name 获取执行函数"""
        return self._executors.get(tool_function_name)

    def list_registered(self) -> list[str]:
        """列出已注册的 Skill 名称"""
        return list(self._tool_defs.keys())

    def __repr__(self) -> str:
        tools = [t for defs in self._tool_defs.values() for t in defs]
        return f"<SkillRegistry skills={list(self._tool_defs.keys())} tools={len(tools)}>"


# 模块级单例
_registry = SkillRegistry.get_instance()


def get_skill_registry() -> SkillRegistry:
    """获取全局 SkillRegistry 单例"""
    return _registry
