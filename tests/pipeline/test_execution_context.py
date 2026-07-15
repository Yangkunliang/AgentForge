"""StageExecutionContext loading and boundary tests."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.models import Artifact, Project, Session, User
from agent_forge.pipeline.catalog import get_stage_definition
from agent_forge.pipeline.execution_context import build_stage_execution_context
from agent_forge.pipeline.service import create_pipeline_run_for_session


async def _create_run(
    db: AsyncSession,
    *,
    user_id: str,
    intent_type: str = "new_feature",
    project_id: str | None = None,
):
    suffix = uuid.uuid4().hex[:8]
    project = Project(
        id=project_id or f"project-stage-context-{suffix}",
        user_id=user_id,
        name=f"stage-context-{suffix}",
        tech_tags=["FastAPI"],
        status="active",
    )
    session = Session(
        id=f"session-stage-context-{suffix}",
        user_id=user_id,
        project_id=project.id,
        title="阶段上下文测试",
        intent_type=intent_type,
    )
    db.add_all([project, session])
    await db.commit()
    run = await create_pipeline_run_for_session(db, session, intent_type)
    await db.commit()
    return project, session, run


def _stage(run, stage_id: str):
    return next(item for item in run.stages if item.stage_id == stage_id)


async def _add_artifact(
    db: AsyncSession,
    *,
    run,
    stage_id: str,
    artifact_id: str,
    artifact_type: str,
    content: str,
    project_id: str | None = None,
    pipeline_run_id: str | None = None,
    created_at: datetime | None = None,
) -> Artifact:
    stage = _stage(run, stage_id)
    artifact = Artifact(
        id=artifact_id,
        project_id=project_id or run.project_id,
        session_id=run.session_id,
        pipeline_run_id=pipeline_run_id or run.id,
        stage_state_id=stage.id,
        artifact_type=artifact_type,
        name=f"{stage.stage_name}.md",
        content=content,
        file_type="markdown",
        metadata_json={"stage_id": stage_id},
    )
    if created_at is not None:
        artifact.created_at = created_at
    db.add(artifact)
    await db.flush()
    return artifact


@pytest.mark.asyncio
async def test_stage_execution_context_loads_only_relevant_previous_run_artifacts(
    db_session: AsyncSession,
    fake_user: User,
):
    project, _session, run = await _create_run(db_session, user_id=fake_user.id)
    current_stage = _stage(run, "backend_dev")
    definition = get_stage_definition("new_feature", "backend_dev")
    assert definition is not None

    expected = [
        await _add_artifact(
            db_session,
            run=run,
            stage_id="analysis",
            artifact_id=f"artifact-prd-{uuid.uuid4().hex[:8]}",
            artifact_type="prd",
            content="已确认需求",
        ),
        await _add_artifact(
            db_session,
            run=run,
            stage_id="design",
            artifact_id=f"artifact-architecture-{uuid.uuid4().hex[:8]}",
            artifact_type="architecture",
            content="已确认架构",
        ),
        await _add_artifact(
            db_session,
            run=run,
            stage_id="db_api",
            artifact_id=f"artifact-api-{uuid.uuid4().hex[:8]}",
            artifact_type="api_spec",
            content="API 契约",
        ),
        await _add_artifact(
            db_session,
            run=run,
            stage_id="task_split",
            artifact_id=f"artifact-plan-{uuid.uuid4().hex[:8]}",
            artifact_type="report",
            content="任务计划",
        ),
    ]
    current_artifact = await _add_artifact(
        db_session,
        run=run,
        stage_id="backend_dev",
        artifact_id=f"artifact-current-{uuid.uuid4().hex[:8]}",
        artifact_type="prd",
        content="当前阶段不应读取",
    )
    future_artifact = await _add_artifact(
        db_session,
        run=run,
        stage_id="testing",
        artifact_id=f"artifact-future-{uuid.uuid4().hex[:8]}",
        artifact_type="prd",
        content="未来阶段不应读取",
    )

    other_session = Session(
        id=f"session-same-project-{uuid.uuid4().hex[:8]}",
        user_id=fake_user.id,
        project_id=project.id,
        title="同项目其他 Run",
        intent_type="new_feature",
    )
    db_session.add(other_session)
    await db_session.commit()
    other_run = await create_pipeline_run_for_session(
        db_session,
        other_session,
        "new_feature",
    )
    await db_session.commit()
    other_run_artifact = await _add_artifact(
        db_session,
        run=other_run,
        stage_id="analysis",
        artifact_id=f"artifact-other-run-{uuid.uuid4().hex[:8]}",
        artifact_type="prd",
        content="其他 Run",
    )
    foreign_project = Project(
        id=f"project-foreign-{uuid.uuid4().hex[:8]}",
        user_id=fake_user.id,
        name="foreign-project",
        tech_tags=[],
        status="active",
    )
    db_session.add(foreign_project)
    await db_session.flush()
    foreign_project_artifact = await _add_artifact(
        db_session,
        run=run,
        stage_id="analysis",
        artifact_id=f"artifact-foreign-project-{uuid.uuid4().hex[:8]}",
        artifact_type="prd",
        content="其他 Project",
        project_id=foreign_project.id,
    )
    await db_session.commit()

    context = await build_stage_execution_context(
        db_session,
        run=run,
        stage=current_stage,
        stage_definition=definition,
    )

    assert [item.artifact_id for item in context.upstream_artifacts] == [
        item.id for item in expected
    ]
    excluded_ids = {
        current_artifact.id,
        future_artifact.id,
        other_run_artifact.id,
        foreign_project_artifact.id,
    }
    assert excluded_ids.isdisjoint(item.artifact_id for item in context.upstream_artifacts)
    assert context.project_id == project.id
    assert context.stage_id == "backend_dev"
    assert context.required_input_artifact_types == (
        "prd",
        "architecture",
        "api_spec",
        "report",
    )
    assert context.missing_input_artifact_types == ()


@pytest.mark.asyncio
async def test_stage_execution_context_keeps_latest_revision_per_stage_and_type(
    db_session: AsyncSession,
    fake_user: User,
):
    _project, _session, run = await _create_run(db_session, user_id=fake_user.id)
    current_stage = _stage(run, "design")
    definition = get_stage_definition("new_feature", "design")
    assert definition is not None
    now = datetime.now(UTC)

    old_artifact = await _add_artifact(
        db_session,
        run=run,
        stage_id="analysis",
        artifact_id=f"artifact-a-old-{uuid.uuid4().hex[:8]}",
        artifact_type="prd",
        content="旧版需求",
        created_at=now - timedelta(minutes=5),
    )
    latest_artifact = await _add_artifact(
        db_session,
        run=run,
        stage_id="analysis",
        artifact_id=f"artifact-z-latest-{uuid.uuid4().hex[:8]}",
        artifact_type="prd",
        content="已确认的最新需求",
        created_at=now,
    )
    await db_session.commit()

    context = await build_stage_execution_context(
        db_session,
        run=run,
        stage=current_stage,
        stage_definition=definition,
        max_artifacts=1,
    )

    assert [item.artifact_id for item in context.upstream_artifacts] == [
        latest_artifact.id
    ]
    assert context.upstream_artifacts[0].content == "已确认的最新需求"
    assert old_artifact.id not in {
        item.artifact_id for item in context.upstream_artifacts
    }


@pytest.mark.asyncio
async def test_stage_execution_context_enforces_artifact_count_and_content_budgets(
    db_session: AsyncSession,
    fake_user: User,
):
    _project, _session, run = await _create_run(db_session, user_id=fake_user.id)
    current_stage = _stage(run, "testing")
    definition = get_stage_definition("new_feature", "testing")
    assert definition is not None
    definition = replace(
        definition,
        required_input_artifact_types=(
            "prd",
            "architecture",
            "api_spec",
            "report",
            "diff",
            "code",
        ),
    )

    source_artifacts = (
        ("analysis", "prd"),
        ("design", "architecture"),
        ("db_api", "api_spec"),
        ("task_split", "report"),
        ("ui_prototype", "diff"),
        ("backend_dev", "code"),
    )
    for index, (stage_id, artifact_type) in enumerate(source_artifacts):
        await _add_artifact(
            db_session,
            run=run,
            stage_id=stage_id,
            artifact_id=f"artifact-budget-{index:02d}-{uuid.uuid4().hex[:8]}",
            artifact_type=artifact_type,
            content=str(index) * 5000,
        )
    await db_session.commit()

    context = await build_stage_execution_context(
        db_session,
        run=run,
        stage=current_stage,
        stage_definition=definition,
    )

    assert len(context.upstream_artifacts) == 6
    assert [len(item.content) for item in context.upstream_artifacts] == [2000] * 6
    assert sum(len(item.content) for item in context.upstream_artifacts) == 12000
    assert all(item.content_truncated for item in context.upstream_artifacts)


@pytest.mark.asyncio
async def test_stage_execution_context_reports_missing_input_types_and_serializes_lists(
    db_session: AsyncSession,
    fake_user: User,
):
    _project, _session, run = await _create_run(db_session, user_id=fake_user.id)
    current_stage = _stage(run, "testing")
    definition = get_stage_definition("new_feature", "testing")
    assert definition is not None
    await _add_artifact(
        db_session,
        run=run,
        stage_id="analysis",
        artifact_id=f"artifact-only-prd-{uuid.uuid4().hex[:8]}",
        artifact_type="prd",
        content="只有需求产物",
    )
    await db_session.commit()

    context = await build_stage_execution_context(
        db_session,
        run=run,
        stage=current_stage,
        stage_definition=definition,
    )
    payload = context.to_context()

    assert context.missing_input_artifact_types == ("code",)
    assert payload["required_input_artifact_types"] == ["prd", "code"]
    assert payload["missing_input_artifact_types"] == ["code"]
    assert payload["expected_output_artifact_types"] == ["test"]
    assert payload["success_criteria"] == [
        "执行目标与相关回归。",
        "记录命令、结果、失败和残余风险。",
    ]
    assert payload["upstream_artifacts"][0]["content"] == "只有需求产物"
