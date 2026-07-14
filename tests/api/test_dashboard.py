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

    async def test_runtime_dashboard_evaluation_stats_include_llm_usage(self, db: AsyncSession):
        suffix = uuid.uuid4().hex[:8]
        user_id = f"dashboard-llm-user-{suffix}"
        project = Project(id=f"dashboard-llm-project-{suffix}", user_id=user_id, name="Dashboard LLM")
        db.add(project)
        for index, (route_key, route_name, stage_id, stage_name, cost) in enumerate(
            [
                ("quality", "Quality Route", "backend_dev", "后端开发", 0.04),
                ("fast", "Fast Route", "analysis", "需求分析", 0.03),
                ("balanced", "Balanced Route", "testing", "回归测试", 0.02),
                ("economy", "Economy Route", "documentation", "文档整理", 0.01),
            ],
            start=1,
        ):
            db.add(
                EvalEvent(
                    id=f"eval-dashboard-llm-{index}-{suffix}",
                    project_id=project.id,
                    pipeline_run_id=f"dashboard-llm-run-{suffix}",
                    stage_id=stage_id,
                    event_type="llm_tool_use_completed",
                    status="success",
                    model_route_key=route_key,
                    model_route_name=route_name,
                    latency_ms=index * 100,
                    cost_usd=cost,
                    tokens_used=index * 100,
                    metadata_json={"stage_name": stage_name},
                )
            )
        await db.commit()

        stats = await _get_evaluation_stats(db, user_id=user_id)

        assert stats.llm.model_dump() == {
            "total_calls": 4,
            "tokens_used": 1000,
            "cost_usd": 0.1,
            "average_latency_ms": 250.0,
            "by_model_route": [
                {
                    "model_route_key": "quality",
                    "name": "Quality Route",
                    "total_calls": 1,
                    "tokens_used": 100,
                    "cost_usd": 0.04,
                    "average_latency_ms": 100.0,
                },
                {
                    "model_route_key": "fast",
                    "name": "Fast Route",
                    "total_calls": 1,
                    "tokens_used": 200,
                    "cost_usd": 0.03,
                    "average_latency_ms": 200.0,
                },
                {
                    "model_route_key": "balanced",
                    "name": "Balanced Route",
                    "total_calls": 1,
                    "tokens_used": 300,
                    "cost_usd": 0.02,
                    "average_latency_ms": 300.0,
                },
            ],
            "by_stage": [
                {
                    "stage_id": "backend_dev",
                    "name": "后端开发",
                    "total_calls": 1,
                    "tokens_used": 100,
                    "cost_usd": 0.04,
                    "average_latency_ms": 100.0,
                },
                {
                    "stage_id": "analysis",
                    "name": "需求分析",
                    "total_calls": 1,
                    "tokens_used": 200,
                    "cost_usd": 0.03,
                    "average_latency_ms": 200.0,
                },
                {
                    "stage_id": "testing",
                    "name": "回归测试",
                    "total_calls": 1,
                    "tokens_used": 300,
                    "cost_usd": 0.02,
                    "average_latency_ms": 300.0,
                },
            ],
        }
