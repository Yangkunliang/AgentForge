"""SQLAlchemy 基础设施：engine、session、declarative base"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import AsyncContextManager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from agent_forge.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncContextManager[AsyncSession]:
    """获取异步数据库会话（FastAPI 依赖注入用）"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def close() -> None:
    """关闭引擎（应用退出时调用）"""
    await engine.dispose()


async def init_db() -> None:
    """初始化数据库连接（启动时调用，用于健康检查等）"""
    async with engine.connect() as conn:
        await conn.execute("SELECT 1")  # type: ignore[no-untyped-call]
