"""健康检查路由"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

import redis.asyncio as redis
from aio_pika import connect
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from agent_forge.config import settings  # noqa: E402
from agent_forge.database import async_session_factory  # noqa: E402

router = APIRouter()
logger = logging.getLogger("agent_forge")


@router.get("/health", tags=["health"])
async def health_check() -> dict[str, Any]:
    """返回各依赖服务的连通状态"""
    result: dict[str, Any] = {"status": "ok", "db": "unknown", "rabbitmq": "unknown", "redis": "unknown"}

    # PostgreSQL
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
            await session.commit()
            result["db"] = "ok"
    except Exception:
        result["db"] = "error"
        result["status"] = "degraded"

    # RabbitMQ
    try:
        conn = await connect(settings.rabbitmq_url, timeout=5)
        await conn.close()
        result["rabbitmq"] = "ok"
    except Exception:
        result["rabbitmq"] = "error"
        result["status"] = "degraded"

    # Redis
    try:
        r = redis.from_url(settings.redis_url, decode_responses=True)
        await r.ping()
        await r.close()
        result["redis"] = "ok"
    except Exception:
        result["redis"] = "error"
        result["status"] = "degraded"

    return result
