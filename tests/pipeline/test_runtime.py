"""Pipeline StageRuntime tests."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.models import Project, User
from agent_forge.models.session import Session
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
