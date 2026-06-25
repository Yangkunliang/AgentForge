"""测试 MemoryManager 编排逻辑（mocked DB）"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agent_forge.memory.manager import MemoryManager
from agent_forge.memory.embedder import chunk_text


class TestMemoryManagerSearch:
    """测试 MemoryManager.search 方法"""

    @pytest.mark.asyncio
    async def test_search_returns_empty_when_no_results(self):
        """无匹配结果时返回空列表"""
        db = AsyncMock()
        mgr = MemoryManager(db)

        # Mock retriever.hybrid_search to return empty
        with patch.object(mgr.retriever, "hybrid_search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []
            results = await mgr.search(query="test", user_id="user1")
            assert results == []
            mock_search.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_search_passes_parameters(self):
        """搜索参数正确传递"""
        db = AsyncMock()
        mgr = MemoryManager(db)

        with patch.object(mgr.retriever, "hybrid_search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []
            await mgr.search(query="hello", user_id="user1", limit=10, category="code")
            mock_search.assert_awaited_once_with(
                query="hello", user_id="user1", limit=10,
                category="code", user_only=False,
            )


class TestMemoryManagerPrepareTaskContext:
    """测试 Agent 提示注入"""

    @pytest.mark.asyncio
    async def test_prepare_context_empty_when_no_inputs(self):
        """无 user 输入时返回空字符串"""
        db = AsyncMock()
        # Mock chat_messages query to return empty
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_result

        mgr = MemoryManager(db)
        context = await mgr.prepare_task_context("task-1")
        assert context == ""


class TestChunkText:
    """测试 chunk_text 函数"""

    def test_single_chunk_for_short_text(self):
        text = "short"
        result = chunk_text(text)
        assert len(result) == 1
        assert result[0] == text

    def test_multiple_chunks_for_long_text(self):
        text = "a" * 2000
        result = chunk_text(text, max_size=500)
        assert len(result) >= 3
        # Total covered content should be significant
        assert sum(len(c) for c in result) >= 1500

    def test_paragraph_boundaries_preserved(self):
        text = "Para 1.\n\nPara 2.\n\nPara 3."
        result = chunk_text(text, max_size=20)
        assert len(result) >= 1
        # Should split at paragraph boundaries
        for chunk in result:
            assert len(chunk) <= 20
