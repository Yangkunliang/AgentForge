"""Evaluation feedback API and service tests."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.evaluation.service import EvaluationService
from agent_forge.models import EvalEvent, Project, User


@pytest.mark.asyncio
async def test_evaluation_service_records_and_summarizes_project_events(
    db: AsyncSession,
    fake_user: User,
):
    project = Project(id="project-eval-service", user_id=fake_user.id, name="Eval Service")
    db.add(project)
    await db.commit()

    await EvaluationService.record_event(
        db,
        project_id=project.id,
        pipeline_run_id="run-1",
        stage_id="analysis",
        event_type="stage_completed",
        status="success",
        latency_ms=1200,
        agent_profile_id="agent-1",
        agent_profile_name="Planner",
        model_route_key="default",
        model_name="gpt-4",
    )
    await EvaluationService.record_event(
        db,
        project_id=project.id,
        pipeline_run_id="run-1",
        event_type="skill_failed",
        status="failed",
        skill_name="code-executor",
        tool_name="code_executor",
        latency_ms=250,
    )
    await EvaluationService.record_event(
        db,
        project_id=project.id,
        pipeline_run_id="run-1",
        event_type="delivery_succeeded",
        status="success",
        delivery_channel="local",
        artifact_id="artifact-1",
    )
    await db.commit()

    summary = await EvaluationService.get_summary(db, user_id=fake_user.id, project_id=project.id)

    assert summary["total_events"] == 3
    assert summary["stages"]["total"] == 1
    assert summary["stages"]["success_rate"] == 1.0
    assert summary["skills"]["failed"] == 1
    assert summary["delivery"]["succeeded"] == 1
    assert summary["agents"][0]["agent_profile_id"] == "agent-1"
    assert summary["models"][0]["model_route_key"] == "default"


@pytest.mark.asyncio
async def test_evaluation_service_summarizes_skill_authorizations(
    db: AsyncSession,
    fake_user: User,
):
    suffix = uuid.uuid4().hex[:8]
    project = Project(id=f"project-auth-summary-{suffix}", user_id=fake_user.id, name="Auth Summary")
    db.add(project)
    await db.commit()

    await EvaluationService.record_event(
        db,
        project_id=project.id,
        pipeline_run_id=f"run-auth-{suffix}",
        stage_id="locate",
        event_type="skill_authorization_required",
        status="blocked",
        skill_name="code-executor",
        tool_name="code_executor",
        metadata={"permissions": ["shell"], "policy_key": "default"},
    )
    await EvaluationService.record_event(
        db,
        project_id=project.id,
        pipeline_run_id=f"run-auth-{suffix}",
        stage_id="locate",
        event_type="skill_authorization_required",
        status="blocked",
        skill_name="http-request",
        tool_name="http_request",
        metadata={"permissions": ["external_side_effect"], "policy_key": "default"},
    )
    await EvaluationService.record_event(
        db,
        project_id=project.id,
        pipeline_run_id=f"run-auth-{suffix}",
        stage_id="locate",
        event_type="skill_authorization_granted",
        status="success",
        skill_name="code-executor",
        tool_name="code_executor",
        metadata={"permissions": ["shell"], "source": "user_confirmation"},
    )
    await EvaluationService.record_event(
        db,
        project_id=project.id,
        pipeline_run_id=f"run-auth-{suffix}",
        event_type="skill_called",
        status="success",
        skill_name="code-executor",
        tool_name="code_executor",
    )
    await db.commit()

    summary = await EvaluationService.get_summary(db, user_id=fake_user.id, project_id=project.id)

    assert summary["skill_authorizations"] == {
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


@pytest.mark.asyncio
async def test_evaluation_service_summarizes_llm_usage(
    db: AsyncSession,
    fake_user: User,
):
    suffix = uuid.uuid4().hex[:8]
    project = Project(id=f"project-llm-summary-{suffix}", user_id=fake_user.id, name="LLM Summary")
    db.add(project)
    await db.commit()

    await EvaluationService.record_event(
        db,
        project_id=project.id,
        pipeline_run_id=f"run-llm-{suffix}",
        stage_id="analysis",
        event_type="llm_tool_use_completed",
        status="success",
        model_route_key="fast",
        model_route_name="Fast Route",
        model_name="openai/gpt-4.1-mini",
        latency_ms=400,
        cost_usd=0.01,
        tokens_used=100,
    )
    await EvaluationService.record_event(
        db,
        project_id=project.id,
        pipeline_run_id=f"run-llm-{suffix}",
        stage_id="backend_dev",
        event_type="llm_tool_use_completed",
        status="success",
        model_route_key="fast",
        model_route_name="Fast Route",
        model_name="openai/gpt-4.1-mini",
        latency_ms=600,
        cost_usd=0.02,
        tokens_used=250,
    )
    await db.commit()

    summary = await EvaluationService.get_summary(db, user_id=fake_user.id, project_id=project.id)

    assert summary["llm"] == {
        "total": 2,
        "succeeded": 2,
        "failed": 0,
        "success_rate": 1.0,
        "average_latency_ms": 500.0,
        "cost_usd": 0.03,
        "tokens_used": 350,
    }
    assert summary["models"][0]["model_route_key"] == "fast"
    assert summary["models"][0]["cost_usd"] == 0.03


@pytest.mark.asyncio
async def test_evaluation_service_summarizes_llm_usage_dimensions(
    db: AsyncSession,
    fake_user: User,
):
    suffix = uuid.uuid4().hex[:8]
    project = Project(id=f"project-llm-dimensions-{suffix}", user_id=fake_user.id, name="LLM Dimensions")
    db.add(project)
    await db.commit()

    events = [
        {
            "stage_id": "analysis",
            "model_route_key": "fast",
            "model_route_name": "Fast Route",
            "latency_ms": 400,
            "cost_usd": 0.01,
            "tokens_used": 100,
            "metadata": {"stage_name": "需求分析"},
        },
        {
            "stage_id": "backend_dev",
            "model_route_key": "quality",
            "model_route_name": "Quality Route",
            "latency_ms": 900,
            "cost_usd": 0.03,
            "tokens_used": 300,
            "metadata": {"stage_name": "后端开发"},
        },
        {
            "stage_id": "backend_dev",
            "model_route_key": "quality",
            "model_route_name": "Quality Route",
            "latency_ms": 500,
            "cost_usd": 0.02,
            "tokens_used": 200,
            "metadata": {"stage_name": "后端开发"},
        },
        {
            "stage_id": "documentation",
            "model_route_key": "economy",
            "model_route_name": None,
            "latency_ms": None,
            "cost_usd": 0.005,
            "tokens_used": 50,
            "metadata": {},
        },
    ]
    for event in events:
        await EvaluationService.record_event(
            db,
            project_id=project.id,
            pipeline_run_id=f"run-llm-dimensions-{suffix}",
            event_type="llm_tool_use_completed",
            status="success",
            **event,
        )
    await EvaluationService.record_event(
        db,
        project_id=project.id,
        pipeline_run_id=f"run-llm-dimensions-{suffix}",
        stage_id="backend_dev",
        event_type="stage_completed",
        status="success",
        model_route_key="quality",
        model_route_name="Quality Route",
        latency_ms=1000,
        cost_usd=9.0,
        tokens_used=9000,
        metadata={"stage_name": "后端开发"},
    )
    await db.commit()

    summary = await EvaluationService.get_summary(db, user_id=fake_user.id, project_id=project.id)

    assert summary["llm_by_model_route"] == [
        {
            "model_route_key": "quality",
            "name": "Quality Route",
            "total_calls": 2,
            "tokens_used": 500,
            "cost_usd": 0.05,
            "average_latency_ms": 700.0,
        },
        {
            "model_route_key": "fast",
            "name": "Fast Route",
            "total_calls": 1,
            "tokens_used": 100,
            "cost_usd": 0.01,
            "average_latency_ms": 400.0,
        },
        {
            "model_route_key": "economy",
            "name": "economy",
            "total_calls": 1,
            "tokens_used": 50,
            "cost_usd": 0.005,
            "average_latency_ms": 0.0,
        },
    ]
    assert summary["llm_by_stage"] == [
        {
            "stage_id": "backend_dev",
            "name": "后端开发",
            "total_calls": 2,
            "tokens_used": 500,
            "cost_usd": 0.05,
            "average_latency_ms": 700.0,
        },
        {
            "stage_id": "analysis",
            "name": "需求分析",
            "total_calls": 1,
            "tokens_used": 100,
            "cost_usd": 0.01,
            "average_latency_ms": 400.0,
        },
        {
            "stage_id": "documentation",
            "name": "documentation",
            "total_calls": 1,
            "tokens_used": 50,
            "cost_usd": 0.005,
            "average_latency_ms": 0.0,
        },
    ]


@pytest.mark.asyncio
async def test_evaluation_summary_api_filters_to_current_user_project(
    async_client: TestClient,
    db: AsyncSession,
    fake_user: User,
):
    own_project = Project(id="project-eval-api", user_id=fake_user.id, name="Eval API")
    other_project = Project(id="project-eval-other", user_id="other-user", name="Other")
    db.add_all([own_project, other_project])
    db.add(
        EvalEvent(
            id="eval-other-user",
            project_id=other_project.id,
            event_type="stage_completed",
            status="success",
        )
    )
    await db.commit()

    await EvaluationService.record_event(
        db,
        project_id=own_project.id,
        pipeline_run_id="run-api",
        event_type="stage_failed",
        status="failed",
        stage_id="backend_dev",
    )
    await db.commit()

    resp = async_client.get(f"/api/v1/evaluation/summary?project_id={own_project.id}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == own_project.id
    assert data["total_events"] == 1
    assert data["stages"]["failed"] == 1


@pytest.mark.asyncio
async def test_safe_record_event_swallows_evaluation_write_failures():
    class BrokenSession:
        async def __aenter__(self):
            raise RuntimeError("eval db down")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    def broken_factory():
        return BrokenSession()

    result = await EvaluationService.safe_record_event(
        broken_factory,
        project_id="project-broken",
        event_type="stage_completed",
        status="success",
    )

    assert result is None
