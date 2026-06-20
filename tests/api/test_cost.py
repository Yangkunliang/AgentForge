"""费用统计 API 测试"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.api.routes.cost import get_daily_cost


@pytest.mark.asyncio
class TestCostAPI:
    async def test_get_daily_cost(self, db: AsyncSession):
        result = await get_daily_cost(db=db)
        assert result.total_cost_usd >= 0
        assert result.total_tasks >= 0
        assert result.avg_cost_per_task >= 0
        assert isinstance(result.model_costs, dict)