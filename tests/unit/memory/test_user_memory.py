"""测试用户记忆 CRUD（get_or_create, update, list）"""

import pytest
from unittest.mock import AsyncMock

from agent_forge.memory.manager import MemoryManager


class TestUserMemoryCRUD:
    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        return db

    @pytest.fixture
    def retriever(self, mock_db):
        return AsyncMock()

    @pytest.fixture
    def mgr(self, mock_db, retriever):
        mgr = MemoryManager(mock_db)
        mgr.retriever = retriever
        return mgr

    @pytest.mark.asyncio
    async def test_update_user_memory_creates_if_not_exists(self, mgr):
        """更新不存在的用户记忆应创建新记录"""
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mgr.db.execute = AsyncMock(return_value=mock_result)

        entry = await mgr.update_user_memory(
            user_id="user1",
            category="preference",
            content="Python is best",
            metadata={"priority": "high"},
        )

        assert entry is not None
        assert entry.category == "preference"
        assert entry.content == "Python is best"
        assert mgr.db.execute.called

    @pytest.mark.asyncio
    async def test_update_user_memory_updates_existing(self, mgr):
        """更新已存在的用户记忆应更新内容"""
        from agent_forge.models import UserMemory

        existing = UserMemory(
            id="um-1",
            user_id="user1",
            category="preference",
            content="Old content",
            updated_at=None,
        )

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = existing
        mgr.db.execute = AsyncMock(return_value=mock_result)

        entry = await mgr.update_user_memory(
            user_id="user1",
            category="preference",
            content="New content",
        )

        assert entry is not None
        assert entry.content == "New content"
        assert entry.id == "um-1"

    @pytest.mark.asyncio
    async def test_get_user_memories_returns_all(self, mgr):
        """获取用户记忆应返回所有记录"""
        from agent_forge.models import UserMemory

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [
            UserMemory(id="1", user_id="u1", category="preference", content="C1", updated_at=None),
            UserMemory(id="2", user_id="u1", category="tech_stack", content="C2", updated_at=None),
        ]
        mgr.db.execute = AsyncMock(return_value=mock_result)

        memories = await mgr.get_user_memories("u1")
        assert len(memories) == 2
        assert memories[0].category == "preference"

    @pytest.mark.asyncio
    async def test_get_or_create_returns_existing(self, mgr):
        """已存在时应返回已有记录"""
        from agent_forge.models import UserMemory

        existing = UserMemory(
            id="um-1",
            user_id="user1",
            category="preference",
            content="Existing content",
        )

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = existing
        mgr.db.execute = AsyncMock(return_value=mock_result)

        entry = await mgr.get_or_create_user_memory(
            user_id="user1",
            category="preference",
            content="New content",
        )

        assert entry.id == "um-1"
        assert entry.content == "Existing content"  # 应返回已有的，不覆盖

    @pytest.mark.asyncio
    async def test_get_or_create_creates_if_missing(self, mgr):
        """不存在时应创建新记录"""
        from agent_forge.models import UserMemory

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mgr.db.execute = AsyncMock(return_value=mock_result)

        entry = await mgr.get_or_create_user_memory(
            user_id="user1",
            category="preference",
            content="New content",
        )

        assert entry is not None
        assert entry.category == "preference"
        assert mgr.db.add.called
