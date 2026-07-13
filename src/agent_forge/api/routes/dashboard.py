"""Dashboard API 路由"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.auth.jwt import get_current_active_user
from agent_forge.database import get_async_session
from agent_forge.evaluation import EvaluationService
from agent_forge.models.agent import Agent
from agent_forge.models.skill import Skill
from agent_forge.models.task import Task, TaskStatus
from agent_forge.models.user import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


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


class CostStats(BaseModel):
    today_usd: float
    trend_pct: float
    daily_7d: list[dict[str, float | str]]


class TaskSummary(BaseModel):
    task_id: str
    description: str
    status: str
    total_cost_usd: float | None
    created_at: str


class SkillAuthorizationDimension(BaseModel):
    required: int
    granted: int
    grant_rate: float


class SkillAuthorizationBySkill(SkillAuthorizationDimension):
    skill_name: str


class SkillAuthorizationByPermission(SkillAuthorizationDimension):
    permission: str


class SkillAuthorizationStats(SkillAuthorizationDimension):
    by_skill: list[SkillAuthorizationBySkill]
    by_permission: list[SkillAuthorizationByPermission]


class EvaluationStats(BaseModel):
    total_events: int
    stage_success_rate: float
    skill_success_rate: float
    delivery_success_rate: float
    average_stage_latency_ms: float
    skill_authorizations: SkillAuthorizationStats


class DashboardResponse(BaseModel):
    tasks: TaskStats
    agents: AgentStats
    skills: SkillStats
    cost: CostStats
    evaluation: EvaluationStats
    recent_tasks: list[TaskSummary]


@router.get("")
async def get_dashboard(
    db: AsyncSession = Depends(get_async_session),
    _: User = Depends(get_current_active_user),
):
    tasks = await _get_task_stats(db)
    agents = await _get_agent_stats(db)
    skills = await _get_skill_stats(db)
    cost = await _get_cost_stats(db)
    evaluation = await _get_evaluation_stats(db, user_id=_.id)
    recent_tasks = await _get_recent_tasks(db)

    return DashboardResponse(
        tasks=tasks,
        agents=agents,
        skills=skills,
        cost=cost,
        evaluation=evaluation,
        recent_tasks=recent_tasks,
    )


async def _get_task_stats(db: AsyncSession) -> TaskStats:
    result = await db.execute(select(func.count(Task.id)))
    total = result.scalar_one()

    pending = await _count_by_status(db, TaskStatus.PENDING)
    processing = await _count_by_status(db, TaskStatus.PROCESSING)
    completed = await _count_by_status(db, TaskStatus.COMPLETED)
    failed = await _count_by_status(db, TaskStatus.FAILED)

    return TaskStats(
        total=total,
        pending=pending,
        processing=processing,
        completed=completed,
        failed=failed,
    )


async def _count_by_status(db: AsyncSession, status: TaskStatus) -> int:
    result = await db.execute(select(func.count(Task.id)).where(Task.status == status))
    return result.scalar_one()


async def _get_agent_stats(db: AsyncSession) -> AgentStats:
    active = await db.execute(
        select(func.count(Agent.id)).where(Agent.status == "active")
    )
    inactive = await db.execute(
        select(func.count(Agent.id)).where(Agent.status == "inactive")
    )
    return AgentStats(active=active.scalar_one(), inactive=inactive.scalar_one())


async def _get_skill_stats(db: AsyncSession) -> SkillStats:
    result = await db.execute(select(func.count(Skill.id)))
    return SkillStats(total=result.scalar_one())


async def _get_cost_stats(db: AsyncSession) -> CostStats:
    today = datetime.now(timezone.utc).date()
    today_str = today.isoformat()

    today_result = await db.execute(
        select(func.coalesce(func.sum(Task.total_cost_usd), 0)).where(
            func.date(Task.created_at) == today
        )
    )
    today_usd = float(today_result.scalar_one() or 0)

    yesterday = (today - timedelta(days=1)).isoformat()
    yesterday_result = await db.execute(
        select(func.coalesce(func.sum(Task.total_cost_usd), 0)).where(
            func.date(Task.created_at) == yesterday
        )
    )
    yesterday_usd = float(yesterday_result.scalar_one() or 0)

    trend_pct = ((today_usd - yesterday_usd) / (yesterday_usd or 1)) * 100

    daily_7d = []
    for i in range(6, -1, -1):
        date = (today - timedelta(days=i)).isoformat()
        result = await db.execute(
            select(func.coalesce(func.sum(Task.total_cost_usd), 0)).where(
                func.date(Task.created_at) == date
            )
        )
        daily_7d.append({"date": date, "usd": float(result.scalar_one() or 0)})

    return CostStats(
        today_usd=round(today_usd, 2),
        trend_pct=round(trend_pct, 1),
        daily_7d=daily_7d,
    )


async def _get_evaluation_stats(db: AsyncSession, user_id: str | None = None) -> EvaluationStats:
    summary = await EvaluationService.get_summary(db, user_id=user_id)
    return EvaluationStats(
        total_events=summary["total_events"],
        stage_success_rate=summary["stages"]["success_rate"],
        skill_success_rate=summary["skills"]["success_rate"],
        delivery_success_rate=summary["delivery"]["success_rate"],
        average_stage_latency_ms=summary["stages"]["average_latency_ms"],
        skill_authorizations=summary["skill_authorizations"],
    )


async def _get_recent_tasks(db: AsyncSession, limit: int = 5) -> list[TaskSummary]:
    result = await db.execute(
        select(Task)
        .order_by(Task.created_at.desc())
        .limit(limit)
    )
    tasks = result.scalars().all()
    return [
        TaskSummary(
            task_id=task.id,
            description=task.description,
            status=task.status,
            total_cost_usd=round(task.total_cost_usd, 2) if task.total_cost_usd else None,
            created_at=task.created_at,
        )
        for task in tasks
    ]
