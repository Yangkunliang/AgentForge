"""内置 Skill 注册器

启动时调用 register_builtin_skills()，将内置 Skill 注册到：
  1. 数据库（SkillManager）
  2. 运行时注册表（SkillRegistry）
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.database import async_session_factory
from agent_forge.skills.manager import SkillManager
from agent_forge.skills.registry import get_skill_registry

logger = logging.getLogger(__name__)


async def register_builtin_skills(db: AsyncSession | None = None) -> None:
    """注册所有内置 Skill（DB + Registry）"""
    close_session = False
    if db is None:
        db = async_session_factory()
        close_session = True

    try:
        registry = get_skill_registry()

        # ── 1. web-search Skill ───────────────────────────────
        from agent_forge.skills.web_search import web_search

        web_search_tool_def = {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": (
                    "搜索互联网获取最新信息。当需要查找最新事件、验证事实、"
                    "检索特定内容时调用。不要凭记忆回答可能过时的信息，使用此工具获取真实数据。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索关键词或问题",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "返回结果数量，默认 5",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            },
        }

        try:
            await SkillManager.register_skill(
                db,
                name="web-search",
                version="1.0.0",
                description="Web search skill supporting DuckDuckGo and SearxNG",
                entry_point="agent_forge.skills.web_search:web_search",
                manifest={"tool": web_search_tool_def["function"]},
                source_type="builtin",
            )
        except Exception as e:
            logger.debug("web-search skill already registered or error: %s", e)

        registry.register(
            skill_name="web-search",
            tool_defs=[web_search_tool_def],
            executors={"web_search": web_search},
        )

        # ── 2. weather Skill ──────────────────────────────────
        from agent_forge.skills.weather import GET_WEATHER_TOOL, get_weather

        try:
            await SkillManager.register_skill(
                db,
                name="weather",
                version="1.0.0",
                description="实时天气查询 Skill（Open-Meteo，免费无 API Key）",
                entry_point="agent_forge.skills.weather:get_weather",
                manifest={"tool": GET_WEATHER_TOOL["function"]},
                source_type="builtin",
            )
        except Exception as e:
            logger.debug("weather skill already registered or error: %s", e)

        registry.register(
            skill_name="weather",
            tool_defs=[GET_WEATHER_TOOL],
            executors={"get_weather": get_weather},
        )

        # ── 3. http-request Skill ──────────────────────────────
        from agent_forge.skills.http_request import HTTP_REQUEST_TOOL, http_request

        try:
            await SkillManager.register_skill(
                db,
                name="http-request",
                version="1.0.0",
                description="HTTP 请求工具，支持 GET/POST/PUT/PATCH/DELETE，可调用任意 REST API",
                entry_point="agent_forge.skills.http_request:http_request",
                manifest={"tool": HTTP_REQUEST_TOOL["function"]},
                source_type="builtin",
            )
        except Exception as e:
            logger.debug("http-request skill already registered or error: %s", e)

        registry.register(
            skill_name="http-request",
            tool_defs=[HTTP_REQUEST_TOOL],
            executors={"http_request": http_request},
        )

        logger.info("Built-in skills registered: %s", registry.list_registered())

    except Exception as e:
        logger.warning("Failed to register built-in skills: %s", e)
    finally:
        if close_session:
            await db.close()
