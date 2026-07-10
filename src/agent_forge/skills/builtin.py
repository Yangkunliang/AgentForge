"""内置 Skill 注册器

启动时调用 register_builtin_skills()，将内置 Skill 注册到：
  1. 数据库（SkillManager）
  2. 运行时注册表（SkillRegistry）
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.database import async_session_factory
from agent_forge.skills.manager import SkillManager
from agent_forge.skills.registry import get_skill_registry
from agent_forge.skills.runtime_spec import SkillRuntimeSpec

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
        web_search_runtime_spec = _builtin_runtime_spec(
            name="web-search",
            version="1.0.0",
            tool_defs=[web_search_tool_def],
            permissions=["network"],
            entry_point="agent_forge.skills.web_search:web_search",
        )

        try:
            await SkillManager.register_skill(
                db,
                name="web-search",
                version="1.0.0",
                description="Web search skill supporting DuckDuckGo and SearxNG",
                entry_point="agent_forge.skills.web_search:web_search",
                manifest={"tool": web_search_tool_def["function"]},
                manifest_hash=web_search_runtime_spec["manifest_hash"],
                permissions=web_search_runtime_spec["permissions"],
                runtime_spec=web_search_runtime_spec,
                source_type="builtin",
            )
        except Exception as e:
            logger.debug("web-search skill already registered or error: %s", e)

        registry.register(
            skill_name="web-search",
            tool_defs=[web_search_tool_def],
            executors={"web_search": web_search},
            runtime_spec=web_search_runtime_spec,
        )

        # ── 2. weather Skill ──────────────────────────────────
        from agent_forge.skills.weather import GET_WEATHER_TOOL, get_weather
        weather_runtime_spec = _builtin_runtime_spec(
            name="weather",
            version="1.0.0",
            tool_defs=[GET_WEATHER_TOOL],
            permissions=["network"],
            entry_point="agent_forge.skills.weather:get_weather",
        )

        try:
            await SkillManager.register_skill(
                db,
                name="weather",
                version="1.0.0",
                description="实时天气查询 Skill（Open-Meteo，免费无 API Key）",
                entry_point="agent_forge.skills.weather:get_weather",
                manifest={"tool": GET_WEATHER_TOOL["function"]},
                manifest_hash=weather_runtime_spec["manifest_hash"],
                permissions=weather_runtime_spec["permissions"],
                runtime_spec=weather_runtime_spec,
                source_type="builtin",
            )
        except Exception as e:
            logger.debug("weather skill already registered or error: %s", e)

        registry.register(
            skill_name="weather",
            tool_defs=[GET_WEATHER_TOOL],
            executors={"get_weather": get_weather},
            runtime_spec=weather_runtime_spec,
        )

        # ── 3. http-request Skill ──────────────────────────────
        from agent_forge.skills.http_request import HTTP_REQUEST_TOOL, http_request
        http_request_runtime_spec = _builtin_runtime_spec(
            name="http-request",
            version="1.0.0",
            tool_defs=[HTTP_REQUEST_TOOL],
            permissions=["network", "external_side_effect"],
            entry_point="agent_forge.skills.http_request:http_request",
        )

        try:
            await SkillManager.register_skill(
                db,
                name="http-request",
                version="1.0.0",
                description="HTTP 请求工具，支持 GET/POST/PUT/PATCH/DELETE，可调用任意 REST API",
                entry_point="agent_forge.skills.http_request:http_request",
                manifest={"tool": HTTP_REQUEST_TOOL["function"]},
                manifest_hash=http_request_runtime_spec["manifest_hash"],
                permissions=http_request_runtime_spec["permissions"],
                runtime_spec=http_request_runtime_spec,
                source_type="builtin",
            )
        except Exception as e:
            logger.debug("http-request skill already registered or error: %s", e)

        registry.register(
            skill_name="http-request",
            tool_defs=[HTTP_REQUEST_TOOL],
            executors={"http_request": http_request},
            runtime_spec=http_request_runtime_spec,
        )

        # ── 4. update-profile Skill ──────────────────────────────
        from agent_forge.skills.update_profile import UPDATE_PROFILE_TOOL, update_profile
        update_profile_runtime_spec = _builtin_runtime_spec(
            name="update-profile",
            version="1.0.0",
            tool_defs=[UPDATE_PROFILE_TOOL],
            permissions=["external_side_effect"],
            entry_point="agent_forge.skills.update_profile:update_profile",
        )

        try:
            await SkillManager.register_skill(
                db,
                name="update-profile",
                version="1.0.0",
                description="更新用户个人资料（昵称、头像）",
                entry_point="agent_forge.skills.update_profile:update_profile",
                manifest={"tool": UPDATE_PROFILE_TOOL["function"]},
                manifest_hash=update_profile_runtime_spec["manifest_hash"],
                permissions=update_profile_runtime_spec["permissions"],
                runtime_spec=update_profile_runtime_spec,
                source_type="builtin",
            )
        except Exception as e:
            logger.debug("update-profile skill already registered or error: %s", e)

        registry.register(
            skill_name="update-profile",
            tool_defs=[UPDATE_PROFILE_TOOL],
            executors={"update_profile": update_profile},
            runtime_spec=update_profile_runtime_spec,
        )

        # ── 5. code-executor Skill ──────────────────────────────
        from agent_forge.skills.code_executor import CODE_EXECUTOR_TOOL, code_executor
        code_executor_runtime_spec = _builtin_runtime_spec(
            name="code-executor",
            version="1.0.0",
            tool_defs=[CODE_EXECUTOR_TOOL],
            permissions=["shell"],
            entry_point="agent_forge.skills.code_executor:code_executor",
        )

        try:
            await SkillManager.register_skill(
                db,
                name="code-executor",
                version="1.0.0",
                description="在隔离沙箱中执行 Python 代码",
                entry_point="agent_forge.skills.code_executor:code_executor",
                manifest={"tool": CODE_EXECUTOR_TOOL["function"]},
                manifest_hash=code_executor_runtime_spec["manifest_hash"],
                permissions=code_executor_runtime_spec["permissions"],
                runtime_spec=code_executor_runtime_spec,
                source_type="builtin",
            )
        except Exception as e:
            logger.debug("code-executor skill already registered or error: %s", e)

        registry.register(
            skill_name="code-executor",
            tool_defs=[CODE_EXECUTOR_TOOL],
            executors={"code_executor": code_executor},
            runtime_spec=code_executor_runtime_spec,
        )

        logger.info("Built-in skills registered: %s", registry.list_registered())

    except Exception as e:
        logger.warning("Failed to register built-in skills: %s", e)
    finally:
        if close_session:
            await db.close()


def _builtin_runtime_spec(
    *,
    name: str,
    version: str,
    tool_defs: list[dict[str, Any]],
    permissions: list[str],
    entry_point: str,
) -> dict[str, Any]:
    return SkillRuntimeSpec(
        name=name,
        version=version,
        source_type="builtin",
        manifest_hash=_builtin_manifest_hash(name, version, tool_defs, permissions),
        tool_defs=tool_defs,
        permissions=permissions,
        executor_kind="python",
        executor_entry_point=entry_point,
        audit_level="standard",
        source="builtin",
    ).to_dict()


def _builtin_manifest_hash(
    name: str,
    version: str,
    tool_defs: list[dict[str, Any]],
    permissions: list[str],
) -> str:
    payload = {
        "name": name,
        "version": version,
        "permissions": permissions,
        "tool_names": [tool["function"]["name"] for tool in tool_defs],
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
