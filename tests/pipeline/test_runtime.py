"""Pipeline StageRuntime tests."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.models import Artifact, Project, User
from agent_forge.models.session import Message, Session
from agent_forge.pipeline.service import create_pipeline_run_for_session, get_pipeline_run_for_user_or_404
from agent_forge.pipeline.runtime import StageRuntime


class FakeSkillEngine:
    def __init__(self):
        self.called = False
        self.kwargs: dict | None = None

    async def run(self, **kwargs):
        self.called = True
        self.kwargs = kwargs

        async def _chunks():
            yield "stage output"

        return _chunks()


@pytest.mark.asyncio
async def test_stage_runtime_calls_skill_engine_and_advances_current_stage(
    db_session: AsyncSession,
    test_session_factory,
    fake_user: User,
):
    user_id = fake_user.id
    project = Project(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name="runtime-test",
        tech_tags=["FastAPI"],
        status="active",
    )
    session = Session(
        id=str(uuid.uuid4()),
        user_id=user_id,
        project_id=project.id,
        title="Runtime 会话",
        intent_type="bug_fix",
    )
    db_session.add_all([project, session])
    await db_session.commit()

    run = await create_pipeline_run_for_session(db_session, session, "bug_fix")
    await db_session.commit()
    run_id = run.id

    fake_engine = FakeSkillEngine()
    runtime = StageRuntime(engine=fake_engine, session_factory=test_session_factory)

    chunks = []
    async for chunk in runtime.run_current_stage(
        task_id="task-runtime",
        pipeline_run_id=run_id,
        user_id=user_id,
        user_message="修复登录报错",
        conversation_history=[],
        tools=[],
        llm=object(),
        config=object(),
        sse_publish=lambda _event_type, _data: None,
        agent_name="CodeSoul",
        advanced_context={"intent": "bug_fix"},
    ):
        chunks.append(chunk)

    assert chunks == ["stage output"]
    assert fake_engine.called is True
    assert fake_engine.kwargs is not None
    assert fake_engine.kwargs["advanced_context"] == {"intent": "bug_fix"}

    db_session.expire_all()
    refreshed = await get_pipeline_run_for_user_or_404(db_session, run_id, user_id)
    stage_by_id = {stage.stage_id: stage for stage in refreshed.stages}
    assert stage_by_id["locate"].status == "completed"
    assert refreshed.status == "running"
    assert refreshed.current_stage_id == "impact_scope"


@pytest.mark.asyncio
async def test_stage_runtime_creates_artifact_for_completed_stage(
    db_session: AsyncSession,
    test_session_factory,
    fake_user: User,
):
    user_id = fake_user.id
    project = Project(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name="artifact-runtime-test",
        tech_tags=["FastAPI"],
        status="active",
    )
    session = Session(
        id=str(uuid.uuid4()),
        user_id=user_id,
        project_id=project.id,
        title="产物归档会话",
        intent_type="bug_fix",
    )
    assistant_msg = Message(
        id=str(uuid.uuid4()),
        session_id=session.id,
        role="assistant",
        content="",
        task_id="task-artifact",
    )
    db_session.add_all([project, session, assistant_msg])
    await db_session.commit()

    run = await create_pipeline_run_for_session(db_session, session, "bug_fix")
    await db_session.commit()

    runtime = StageRuntime(engine=FakeSkillEngine(), session_factory=test_session_factory)

    chunks = []
    async for chunk in runtime.run_current_stage(
        task_id="task-artifact",
        pipeline_run_id=run.id,
        user_id=user_id,
        user_message="修复登录报错",
        conversation_history=[],
        tools=[],
        llm=object(),
        config=object(),
        sse_publish=lambda _event_type, _data: None,
        agent_name="CodeSoul",
        advanced_context={"intent": "bug_fix"},
        source_message_id=assistant_msg.id,
    ):
        chunks.append(chunk)

    assert chunks == ["stage output"]

    result = await db_session.execute(
        select(Artifact).where(Artifact.pipeline_run_id == run.id)
    )
    artifacts = result.scalars().all()
    assert len(artifacts) == 1

    artifact = artifacts[0]
    assert artifact.project_id == project.id
    assert artifact.session_id == session.id
    assert artifact.pipeline_run_id == run.id
    assert artifact.stage_state_id
    assert artifact.source_message_id == assistant_msg.id
    assert artifact.artifact_type == "report"
    assert artifact.file_type == "markdown"
    assert artifact.name == "问题定位.md"
    assert artifact.content == "stage output"
    assert artifact.metadata_json == {
        "intent_type": "bug_fix",
        "stage_id": "locate",
        "stage_name": "问题定位",
        "stage_order": 0,
        "task_id": "task-artifact",
        "origin": "stage_runtime",
    }
