"""Web Search Skill 单元测试"""

from __future__ import annotations

import pytest
from unittest.mock import patch, AsyncMock

from agent_forge.skills.web_search import web_search


@pytest.mark.asyncio
class TestWebSearch:
    """Web Search 功能测试"""

    async def test_search_basic(self):
        result = await web_search("python fastapi", max_results=3)
        assert isinstance(result, list)
        for item in result:
            assert "title" in item
            assert "snippet" in item
            assert "url" in item

    async def test_search_empty_query(self):
        result = await web_search("", max_results=1)
        assert isinstance(result, list)

    async def test_search_max_results(self):
        result = await web_search("machine learning", max_results=1)
        assert isinstance(result, list)
        assert len(result) <= 1