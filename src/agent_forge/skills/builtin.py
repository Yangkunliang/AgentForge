"""Web search skill — register as built-in skill at startup."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.database import async_session_factory
from agent_forge.skills.manager import SkillManager

logger = logging.getLogger(__name__)


async def register_builtin_skills(db: AsyncSession | None = None) -> None:
    """Register built-in skills at application startup."""
    close_session = False
    if db is None:
        db = async_session_factory()
        close_session = True

    try:
        await SkillManager.register_skill(
            db,
            name="web-search",
            version="1.0.0",
            description="Web search skill supporting DuckDuckGo and SearxNG",
            entry_point="agent_forge.skills.web_search:web_search",
            manifest={
                "tool": {
                    "name": "web_search",
                    "description": "Search the internet for the latest information. Call this when you need to look up fresh content, verify facts, or retrieve specific information.",
                    "parameters": {
                        "query": {
                            "type": "string",
                            "description": "Search keywords or question",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Number of results to return (default 5)",
                            "default": 5,
                        },
                    },
                },
            },
        )
        logger.info("Registered built-in skills")
    except Exception as e:
        logger.warning("Failed to register built-in skills: %s", e)
    finally:
        if close_session:
            await db.close()
