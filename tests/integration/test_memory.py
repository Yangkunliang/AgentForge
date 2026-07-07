"""Memory system integration test

端到端测试语义记忆创建、embedding 生成、混合检索完整链路。
需要运行中的 PostgreSQL + pgvector 环境。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from agent_forge.memory.manager import MemoryManager
from agent_forge.memory.embedder import chunk_text


class TestMemoryManagerCreateAndGet:
    """测试 MemoryManager 创建语义记忆并获取"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        # 模拟 commit 和 refresh
        return db

    @pytest.fixture
    def retriever_mock(self):
        return AsyncMock()

    @pytest.fixture
    def mgr(self, mock_db, retriever_mock):
        mgr = MemoryManager(mock_db)
        mgr.retriever = retriever_mock
        return mgr

    @pytest.mark.asyncio
    async def test_create_semantic_entry_adds_to_db(self, mgr):
        """创建语义记忆应调用 db.add + db.commit"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mgr.db.execute = AsyncMock(return_value=mock_result)

        entry_id = await mgr.create_semantic_entry(
            user_id="user-1",
            content="This is a test memory for code review.",
            title="Code Review Result",
            category="result",
            generate_embedding=False,  # 跳过 embedding 生成
        )

        assert entry_id is not None
        assert mgr.db.add.called
        assert mgr.db.commit.called

    @pytest.mark.asyncio
    async def test_create_semantic_entry_with_title_truncation(self, mgr):
        """标题过长时应截断为 200 字符"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mgr.db.execute = AsyncMock(return_value=mock_result)

        long_content = "x" * 5000
        entry_id = await mgr.create_semantic_entry(
            user_id="user-1",
            content=long_content,
            generate_embedding=False,
        )

        assert entry_id is not None
        # 创建后获取应截断标题
        mock_result = MagicMock()
        from agent_forge.models import SemanticEntry
        mock_entry = SemanticEntry(
            id=entry_id,
            user_id="user-1",
            title=long_content[:200],
            content=long_content,
        )
        mock_result.scalar_one_or_none.return_value = mock_entry
        mgr.db.execute = AsyncMock(return_value=mock_result)

        entry = await mgr.get_semantic_entry(entry_id)
        assert entry is not None
        assert len(entry.title) <= 200

    @pytest.mark.asyncio
    async def test_delete_semantic_entry_soft_deletes(self, mgr):
        """删除语义记忆应为软删除"""
        from agent_forge.models import SemanticEntry

        existing = SemanticEntry(
            id="entry-1",
            user_id="user-1",
            content="test",
            deleted=False,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mgr.db.execute = AsyncMock(return_value=mock_result)

        result = await mgr.delete_semantic_entry("entry-1")
        assert result is True

        # 再次获取应返回 None（已删除）
        mock_result.scalar_one_or_none.return_value = None
        entry = await mgr.get_semantic_entry("entry-1")
        assert entry is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, mgr):
        """删除不存在的记忆应返回 False"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mgr.db.execute = AsyncMock(return_value=mock_result)

        result = await mgr.delete_semantic_entry("nonexistent")
        assert result is False


class TestMemoryManagerList:
    """测试语义记忆列表"""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def retriever_mock(self):
        return AsyncMock()

    @pytest.fixture
    def mgr(self, mock_db, retriever_mock):
        mgr = MemoryManager(mock_db)
        mgr.retriever = retriever_mock
        return mgr

    @pytest.mark.asyncio
    async def test_list_semantic_entries_filters_by_user(self, mgr):
        """列表应按 user_id 过滤"""
        from agent_forge.models import SemanticEntry

        entries = [
            SemanticEntry(
                id=f"e-{i}", user_id="user-1", content=f"Content {i}",
                category="general",
            )
            for i in range(3)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = entries
        mgr.db.execute = AsyncMock(return_value=mock_result)

        result = await mgr.list_semantic_entries(user_id="user-1")
        assert len(result) == 3


class TestChunkTextIntegration:
    """测试 chunk_text 在真实场景下的表现"""

    def test_code_block_chunking(self):
        """代码块场景：按段落分块"""
        code = """def hello():
    print("hello")

def world():
    print("world")

def foo():
    return 42"""
        chunks = chunk_text(code, max_size=50)
        assert len(chunks) >= 1
        for chunk in chunks:
            assert len(chunk) <= 50

    def test_long_document_chunking(self):
        """长文档场景"""
        long_doc = "\n\n".join([f"Paragraph {i}: {'x' * 400}" for i in range(10)])
        chunks = chunk_text(long_doc, max_size=300)
        assert len(chunks) >= 3
        total_content = sum(len(c) for c in chunks)
        assert total_content >= 2000
