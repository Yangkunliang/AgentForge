"""Dashboard API 测试"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes import dashboard as runtime_dashboard
from api.routes.dashboard import (
    _agent_stats as _get_agent_stats,
    _cost_stats as _get_cost_stats,
    _get_evaluation_stats,
    _recent_tasks as _get_recent_tasks,
    _skill_stats as _get_skill_stats,
    _task_stats as _get_task_stats,
)
from agent_forge.api.routes import dashboard as legacy_dashboard
from agent_forge.models.agent import Agent
from agent_forge.models.evaluation import EvalEvent
from agent_forge.models.project import Project
from agent_forge.models.skill import Skill
from agent_forge.models.task import Task, TaskStatus


def test_legacy_dashboard_module_reexports_runtime_dashboard():
    assert legacy_dashboard.router is runtime_dashboard.router
    assert legacy_dashboard._get_evaluation_stats is runtime_dashboard._get_evaluation_stats


@pytest.mark.asyncio
class TestDashboardStats:
    async def test_get_task_stats(self, db: AsyncSession):
        stats = await _get_task_stats(db)
        assert stats.total >= 0
        assert stats.pending >= 0
        assert stats.processing >= 0
        assert stats.completed >= 0
        assert stats.failed >= 0

    async def test_get_agent_stats(self, db: AsyncSession):
        agent1 = Agent(id="agent-1", name="test-agent-1", capabilities=["test"], model="gpt-4", status="active")
        agent2 = Agent(id="agent-2", name="test-agent-2", capabilities=["test"], model="gpt-4", status="inactive")
        db.add(agent1)
        db.add(agent2)
        await db.commit()

        stats = await _get_agent_stats(db)
        assert stats.active >= 1
        assert stats.inactive >= 1

    async def test_get_skill_stats(self, db: AsyncSession):
        from sqlalchemy import select

        result = await db.execute(select(Skill).where(Skill.name == "test-skill"))
        existing = result.scalar_one_or_none()
        if existing:
            await db.delete(existing)
            await db.commit()

        skill = Skill(id="skill-dashboard-test", name="test-skill", version="1.0.0", description="Test", entry_point="test.main")
        db.add(skill)
        await db.commit()

        stats = await _get_skill_stats(db)
        assert stats.total >= 1

    async def test_get_cost_stats(self, db: AsyncSession):
        stats = await _get_cost_stats(db)
        assert stats.today_usd >= 0
        assert len(stats.daily_7d) == 7

    async def test_get_recent_tasks(self, db: AsyncSession):
        tasks = await _get_recent_tasks(db)
        assert isinstance(tasks, list)

    async def test_get_evaluation_stats(self, db: AsyncSession):
        db.add(
            EvalEvent(
                id="eval-dashboard-test",
                project_id="dashboard-project",
                event_type="stage_completed",
                status="success",
                latency_ms=100,
            )
        )
        await db.commit()

        stats = await _get_evaluation_stats(db)

        assert stats.total_events >= 1
        assert stats.stage_success_rate >= 0

    async def test_runtime_dashboard_evaluation_stats_include_skill_authorizations(self, db: AsyncSession):
        suffix = uuid.uuid4().hex[:8]
        user_id = f"dashboard-auth-user-{suffix}"
        project = Project(id=f"dashboard-auth-project-{suffix}", user_id=user_id, name="Dashboard Auth")
        db.add(project)
        db.add_all(
            [
                EvalEvent(
                    id=f"eval-dashboard-auth-required-code-{suffix}",
                    project_id=project.id,
                    event_type="skill_authorization_required",
                    status="blocked",
                    skill_name="code-executor",
                    tool_name="code_executor",
                    metadata_json={"permissions": ["shell"]},
                ),
                EvalEvent(
                    id=f"eval-dashboard-auth-required-http-{suffix}",
                    project_id=project.id,
                    event_type="skill_authorization_required",
                    status="blocked",
                    skill_name="http-request",
                    tool_name="http_request",
                    metadata_json={"permissions": ["external_side_effect"]},
                ),
                EvalEvent(
                    id=f"eval-dashboard-auth-granted-code-{suffix}",
                    project_id=project.id,
                    event_type="skill_authorization_granted",
                    status="success",
                    skill_name="code-executor",
                    tool_name="code_executor",
                    metadata_json={"permissions": ["shell"]},
                ),
            ]
        )
        await db.commit()

        stats = await _get_evaluation_stats(db, user_id=user_id)

        assert stats.skill_authorizations.model_dump() == {
            "required": 2,
            "granted": 1,
            "grant_rate": 0.5,
            "by_skill": [
                {
                    "skill_name": "code-executor",
                    "required": 1,
                    "granted": 1,
                    "grant_rate": 1.0,
                },
                {
                    "skill_name": "http-request",
                    "required": 1,
                    "granted": 0,
                    "grant_rate": 0.0,
                },
            ],
            "by_permission": [
                {
                    "permission": "shell",
                    "required": 1,
                    "granted": 1,
                    "grant_rate": 1.0,
                },
                {
                    "permission": "external_side_effect",
                    "required": 1,
                    "granted": 0,
                    "grant_rate": 0.0,
                },
            ],
        }
