"""费用统计 API 路由"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.auth.jwt import get_current_active_user
from agent_forge.database import get_async_session
from agent_forge.models.task import Task
from agent_forge.models.task_execution import TaskExecution
from agent_forge.models.user import User

router = APIRouter(prefix="/cost", tags=["cost"])


class DailyCostResponse(BaseModel):
    date: str
    total_cost_usd: float
    model_costs: dict[str, float]
    total_tasks: int
    avg_cost_per_task: float


@router.get("")
async def get_daily_cost(
    date: str | None = None,
    db: AsyncSession = Depends(get_async_session),
    _: User = Depends(get_current_active_user),
):
    if date is None:
        date = datetime.now(timezone.utc).date().isoformat()

    total_cost_result = await db.execute(
        select(func.coalesce(func.sum(Task.total_cost_usd), 0)).where(
            func.date(Task.created_at) == date
        )
    )
    total_cost_usd = float(total_cost_result.scalar_one() or 0)

    total_tasks_result = await db.execute(
        select(func.count(Task.id)).where(func.date(Task.created_at) == date)
    )
    total_tasks = total_tasks_result.scalar_one()

    model_costs_result = await db.execute(
        select(
            TaskExecution.model_used,
            func.coalesce(func.sum(TaskExecution.cost_usd), 0).label("total_cost"),
        )
        .join(Task, TaskExecution.task_id == Task.id)
        .where(func.date(Task.created_at) == date)
        .group_by(TaskExecution.model_used)
    )
    model_costs = {}
    for row in model_costs_result.all():
        model_costs[row.model_used or "unknown"] = round(float(row.total_cost or 0), 2)

    avg_cost_per_task = round(total_cost_usd / max(total_tasks, 1), 2)

    return DailyCostResponse(
        date=date,
        total_cost_usd=round(total_cost_usd, 2),
        model_costs=model_costs,
        total_tasks=total_tasks,
        avg_cost_per_task=avg_cost_per_task,
    )