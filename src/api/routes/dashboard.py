"""Dashboard 聚合统计路由"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.database import get_async_session
from agent_forge.models import Agent, Skill, Task, TaskStatus, User
from middleware.auth import get_current_user

router = APIRouter()
logger = logging.getLogger("agent_forge")


# ── 响应 Schema ──────────────────────────────────────────────

class TaskStats(BaseModel):
    total: int
    pending: int
    processing: int
    completed: int
    failed: int


class AgentStats(BaseModel):
    active: int
    inactive: int


class SkillStats(BaseModel):
    total: int


class DailyCost(BaseModel):
    date: str
    usd: float


class CostStats(BaseModel):
    today_usd: float
    trend_pct: float
    daily_7d: list[DailyCost]


class RecentTask(BaseModel):
    task_id: str
    description: str
    status: str
    total_cost_usd: float | None
    created_at: str


class DashboardResponse(BaseModel):
    tasks: TaskStats
    agents: AgentStats
    skills: SkillStats
    cost: CostStats
    recent_tasks: list[RecentTask]


# ── 端点 ─────────────────────────────────────────────────────

@router.get("")
async def get_dashboard(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    task_stats = await _task_stats(db)
    agent_stats = await _agent_stats(db)
    skill_stats = await _skill_stats(db)
    cost_stats = await _cost_stats(db)
    recent = await _recent_tasks(db)

    return DashboardResponse(
        tasks=task_stats,
        agents=agent_stats,
        skills=skill_stats,
        cost=cost_stats,
        recent_tasks=recent,
    ).model_dump()


# ── 内部 helper ──────────────────────────────────────────────

async def _count_by_status(db: AsyncSession, status: TaskStatus) -> int:
    result = await db.execute(select(func.count(Task.id)).where(Task.status == status))
    return int(result.scalar_one() or 0)


async def _task_stats(db: AsyncSession) -> TaskStats:
    total_r = await db.execute(select(func.count(Task.id)))
    total = int(total_r.scalar_one() or 0)
    return TaskStats(
        total=total,
        pending=await _count_by_status(db, TaskStatus.PENDING),
        processing=await _count_by_status(db, TaskStatus.PROCESSING),
        completed=await _count_by_status(db, TaskStatus.COMPLETED),
        failed=await _count_by_status(db, TaskStatus.FAILED),
    )


async def _agent_stats(db: AsyncSession) -> AgentStats:
    total_r = await db.execute(select(func.count(Agent.id)))
    total = int(total_r.scalar_one() or 0)
    return AgentStats(active=total, inactive=0)


async def _skill_stats(db: AsyncSession) -> SkillStats:
    result = await db.execute(select(func.count(Skill.id)))
    return SkillStats(total=int(result.scalar_one() or 0))


async def _sum_cost_on_date(db: AsyncSession, d) -> float:
    result = await db.execute(
        select(func.coalesce(func.sum(Task.total_cost_usd), 0)).where(
            func.date(Task.created_at) == d
        )
    )
    return float(result.scalar_one() or 0)


async def _cost_stats(db: AsyncSession) -> CostStats:
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)

    today_usd = await _sum_cost_on_date(db, today)
    yesterday_usd = await _sum_cost_on_date(db, yesterday)

    if yesterday_usd > 0:
        trend_pct = ((today_usd - yesterday_usd) / yesterday_usd) * 100
    else:
        trend_pct = 0.0 if today_usd == 0 else 100.0

    daily_7d: list[DailyCost] = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        daily_7d.append(DailyCost(date=day.isoformat(), usd=await _sum_cost_on_date(db, day)))

    return CostStats(
        today_usd=round(today_usd, 2),
        trend_pct=round(trend_pct, 1),
        daily_7d=daily_7d,
    )


async def _recent_tasks(db: AsyncSession, limit: int = 5) -> list[RecentTask]:
    result = await db.execute(
        select(Task).order_by(Task.created_at.desc()).limit(limit)
    )
    tasks = result.scalars().all()
    out: list[RecentTask] = []
    for task in tasks:
        created_at = task.created_at
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        out.append(
            RecentTask(
                task_id=task.id,
                description=task.description,
                status=task.status.value if hasattr(task.status, "value") else str(task.status),
                total_cost_usd=round(float(task.total_cost_usd), 2) if task.total_cost_usd else None,
                created_at=created_at,
            )
        )
    return out
