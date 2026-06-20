"""全局 pytest fixtures"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agent_forge.auth.jwt import hash_password
from agent_forge.models import User
from agent_forge.models.base import Base


@pytest.fixture(scope="session")
def event_loop():
    """为 async fixture 创建 session 级别的事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """测试数据库 URL — 使用 SQLite 内存数据库，使用同一文件保证共享"""
    return "sqlite+aiosqlite:///./test_db.sqlite"


@pytest_asyncio.fixture(scope="session")
async def test_engine(test_database_url: str):
    """测试用异步引擎（session 级别，一次创建）"""
    engine = create_async_engine(test_database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def test_session_factory(test_engine):
    """测试用 session factory（共享同一引擎）"""
    return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session(test_session_factory) -> AsyncGenerator[AsyncSession, None]:
    """每个测试后自动回滚的数据库会话"""
    async with test_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def db(db_session: AsyncSession) -> AsyncSession:
    """别名：更简洁的 db fixture"""
    return db_session


@pytest_asyncio.fixture
async def fake_user(db_session: AsyncSession) -> User:
    """工厂函数：创建测试用户"""
    from sqlalchemy import select
    
    result = await db_session.execute(select(User).where(User.username == "testuser"))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        return existing_user
    
    user = User(
        id="test-user-001",
        username="testuser",
        email="test@example.com",
        password_hash=hash_password("TestPass123"),
        permissions=["read", "admin"],
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def async_client(test_session_factory, fake_user):
    """FastAPI TestClient wrapper for API tests"""
    from agent_forge.database import get_async_session
    from fastapi.testclient import TestClient

    from api.main import app
    from middleware.auth import get_current_user

    async def override_get_session():
        async with test_session_factory() as session:
            yield session

    async def override_get_current_user():
        return fake_user

    app.dependency_overrides[get_async_session] = override_get_session
    app.dependency_overrides[get_current_user] = override_get_current_user

    client = TestClient(app, raise_server_exceptions=True)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()
