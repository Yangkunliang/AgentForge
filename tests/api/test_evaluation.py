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
