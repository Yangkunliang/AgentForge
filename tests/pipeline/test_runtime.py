"""Pipeline StageRuntime tests."""

from __future__ import annotations

import uuid
from dataclasses import replace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.models import (
    Agent,
    AgentSkill,
    Artifact,
    EvalEvent,
    LLMCredential,
    LLMModelSetting,
    LLMProviderSetting,
    LLMRoute,
    Project,
    Skill,
    User,
)
from agent_forge.models.session import Message, Session
from agent_forge.pipeline import runtime as runtime_module
from agent_forge.pipeline.catalog import get_stage_definition
from agent_forge.pipeline.service import create_pipeline_run_for_session, get_pipeline_run_for_user_or_404
from agent_forge.pipeline.runtime import StageRuntime
from agent_forge.security.credentials import encrypt_secret
from agent_forge.skills.registry import get_skill_registry


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


def _tool_def(name: str) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"{name} test tool",
            "parameters": {"type": "object", "properties": {}},
        },
    }


async def _test_executor(**_kwargs):
    return {"ok": True}


@pytest.mark.asyncio
async def test_stage_runtime_calls_skill_engine_and_advances_current_stage(
    db_session: AsyncSession,
    test_session_factory,
    fake_user: User,
):
    user_id = fake_user.id
    provider_key = f"anthropic-{uuid.uuid4().hex[:8]}"
    route_key = f"runtime-{uuid.uuid4().hex[:8]}"
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
    assert fake_engine.kwargs["advanced_context"]["intent"] == "bug_fix"
    assert fake_engine.kwargs["advanced_context"]["agent_profile"]["id"]
    assert fake_engine.kwargs["advanced_context"]["stage_execution"] == {
        "project_id": project.id,
        "session_id": session.id,
        "pipeline_run_id": run_id,
        "intent_type": "bug_fix",
        "stage_id": "locate",
        "stage_name": "问题定位",
        "stage_order": 0,
        "description": "定位问题现象、复现条件和根因假设。",
        "required_input_artifact_types": [],
        "expected_output_artifact_types": ["report"],
        "success_criteria": [
            "给出可复现现象和根因证据。",
            "区分事实与假设。",
        ],
        "missing_input_artifact_types": [],
        "upstream_artifacts": [],
    }

    db_session.expire_all()
    refreshed = await get_pipeline_run_for_user_or_404(db_session, run_id, user_id)
    stage_by_id = {stage.stage_id: stage for stage in refreshed.stages}
    assert stage_by_id["locate"].status == "completed"
    assert refreshed.status == "running"
    assert refreshed.current_stage_id == "impact_scope"


@pytest.mark.asyncio
async def test_stage_runtime_records_resolved_agent_profile(
    db_session: AsyncSession,
    test_session_factory,
    fake_user: User,
):
    user_id = fake_user.id
    provider_key = f"anthropic-{uuid.uuid4().hex[:8]}"
    model_key = f"anthropic/claude-3-5-sonnet-{uuid.uuid4().hex[:8]}"
    route_key = f"runtime-{uuid.uuid4().hex[:8]}"
    project = Project(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name="agent-runtime-test",
        tech_tags=["FastAPI"],
        status="active",
    )
    session = Session(
        id=str(uuid.uuid4()),
        user_id=user_id,
        project_id=project.id,
        title="Agent 运行时会话",
        intent_type="bug_fix",
    )
    agent = Agent(
        id=str(uuid.uuid4()),
        name=f"Research Agent {uuid.uuid4()}",
        capabilities=["research"],
        model="claude-3-sonnet",
        status="active",
    )
    db_session.add_all([project, session, agent])
    await db_session.commit()
    agent_id = agent.id
    agent_name = agent.name

    run = await create_pipeline_run_for_session(db_session, session, "bug_fix")
    await db_session.commit()
    run_id = run.id

    fake_engine = FakeSkillEngine()
    runtime = StageRuntime(engine=fake_engine, session_factory=test_session_factory)

    chunks = []
    async for chunk in runtime.run_current_stage(
        task_id="task-agent-runtime",
        pipeline_run_id=run_id,
        user_id=user_id,
        user_message="分析报错",
        conversation_history=[],
        tools=[],
        llm=object(),
        config=object(),
        sse_publish=lambda _event_type, _data: None,
        agent_name="CodeSoul",
        advanced_context={"intent": "bug_fix", "agent_profile_id": agent_id},
    ):
        chunks.append(chunk)

    assert chunks == ["stage output"]
    assert fake_engine.kwargs is not None
    assert fake_engine.kwargs["agent_name"] == agent_name
    assert fake_engine.kwargs["advanced_context"]["agent_profile"] == {
        "id": agent_id,
        "name": agent_name,
        "source": "user_override",
        "capabilities": ["research"],
        "model_name": "claude-3-sonnet",
        "default_model_route_key": "default",
        "allowed_skill_names": [],
    }

    db_session.expire_all()
    refreshed = await get_pipeline_run_for_user_or_404(db_session, run_id, user_id)
    stage_by_id = {stage.stage_id: stage for stage in refreshed.stages}
    assert stage_by_id["locate"].agent_profile_id == agent_id
    assert stage_by_id["locate"].agent_profile_name == agent_name


@pytest.mark.asyncio
async def test_stage_runtime_filters_tools_by_stage_policy_and_agent_allowed_skills(
    db_session: AsyncSession,
    test_session_factory,
    fake_user: User,
):
    user_id = fake_user.id
    project = Project(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name="skill-policy-runtime-test",
        tech_tags=["FastAPI"],
        status="active",
    )
    session = Session(
        id=str(uuid.uuid4()),
        user_id=user_id,
        project_id=project.id,
        title="Skill Policy 运行时会话",
        intent_type="bug_fix",
    )
    agent = Agent(
        id=str(uuid.uuid4()),
        name=f"Policy Agent {uuid.uuid4()}",
        capabilities=["research"],
        model="claude-3-sonnet",
        status="active",
    )
    safe_skill = Skill(
        id=str(uuid.uuid4()),
        name=f"safe-skill-{uuid.uuid4().hex[:8]}",
        version="1.0.0",
        description="safe project context skill",
        permissions=["project_context"],
        runtime_spec={},
        enabled=True,
        source_type="local",
    )
    shell_skill = Skill(
        id=str(uuid.uuid4()),
        name=f"shell-skill-{uuid.uuid4().hex[:8]}",
        version="1.0.0",
        description="shell skill",
        permissions=["shell"],
        runtime_spec={},
        enabled=True,
        source_type="local",
    )
    agent_skill = AgentSkill(agent_id=agent.id, skill_id=safe_skill.id, enabled=True)
    db_session.add_all([project, session, agent, safe_skill, shell_skill, agent_skill])
    await db_session.commit()
    agent_id = agent.id
    safe_skill_name = safe_skill.name
    shell_skill_name = shell_skill.name

    safe_tool = _tool_def("runtime_safe_tool")
    shell_tool = _tool_def("runtime_shell_tool")
    registry = get_skill_registry()
    registry.register(
        skill_name=safe_skill_name,
        tool_defs=[safe_tool],
        executors={"runtime_safe_tool": _test_executor},
        runtime_spec={
            "name": safe_skill_name,
            "version": "1.0.0",
            "source_type": "local",
            "manifest_hash": "safe-runtime-hash",
            "permissions": ["project_context"],
            "executor_kind": "python",
        },
    )
    registry.register(
        skill_name=shell_skill_name,
        tool_defs=[shell_tool],
        executors={"runtime_shell_tool": _test_executor},
        runtime_spec={
            "name": shell_skill_name,
            "version": "1.0.0",
            "source_type": "local",
            "manifest_hash": "shell-runtime-hash",
            "permissions": ["shell"],
            "executor_kind": "python",
        },
    )

    try:
        run = await create_pipeline_run_for_session(db_session, session, "bug_fix")
        await db_session.commit()
        run_id = run.id

        fake_engine = FakeSkillEngine()
        runtime = StageRuntime(engine=fake_engine, session_factory=test_session_factory)

        chunks = []
        async for chunk in runtime.run_current_stage(
            task_id="task-skill-policy-runtime",
            pipeline_run_id=run_id,
            user_id=user_id,
            user_message="分析报错",
            conversation_history=[],
            tools=[safe_tool, shell_tool],
            llm=object(),
            config=object(),
            sse_publish=lambda _event_type, _data: None,
            agent_name="CodeSoul",
            advanced_context={"intent": "bug_fix", "agent_profile_id": agent_id},
        ):
            chunks.append(chunk)
    finally:
        registry.unregister(safe_skill_name)
        registry.unregister(shell_skill_name)

    assert chunks == ["stage output"]
    assert fake_engine.kwargs is not None
    assert [tool["function"]["name"] for tool in fake_engine.kwargs["tools"]] == ["runtime_safe_tool"]
    policy_context = fake_engine.kwargs["advanced_context"]["skill_policy"]
    assert policy_context["policy_key"] == "default"
    assert policy_context["input_tool_count"] == 2
    assert policy_context["allowed_tool_count"] == 1
    assert policy_context["agent_allowed_skill_names"] == [safe_skill_name]
    assert policy_context["excluded_tools"] == [
        {
            "tool_name": "runtime_shell_tool",
            "skill_name": shell_skill_name,
            "reason": "agent_not_allowed",
            "permissions": ["shell"],
        }
    ]


@pytest.mark.asyncio
async def test_stage_runtime_passes_temporary_high_risk_skill_authorization(
    db_session: AsyncSession,
    test_session_factory,
    fake_user: User,
):
    user_id = fake_user.id
    project = Project(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name="high-risk-skill-auth-runtime-test",
        tech_tags=["FastAPI"],
        status="active",
    )
    session = Session(
        id=str(uuid.uuid4()),
        user_id=user_id,
        project_id=project.id,
        title="高风险 Skill 授权运行时会话",
        intent_type="bug_fix",
    )
    agent = Agent(
        id=str(uuid.uuid4()),
        name=f"Authorized Shell Agent {uuid.uuid4()}",
        capabilities=["testing"],
        model="claude-3-sonnet",
        status="active",
    )
    shell_skill = Skill(
        id=str(uuid.uuid4()),
        name=f"authorized-shell-skill-{uuid.uuid4().hex[:8]}",
        version="1.0.0",
        description="temporary shell skill",
        permissions=["shell"],
        runtime_spec={},
        enabled=True,
        source_type="local",
    )
    agent_skill = AgentSkill(agent_id=agent.id, skill_id=shell_skill.id, enabled=True)
    db_session.add_all([project, session, agent, shell_skill, agent_skill])
    await db_session.commit()
    agent_id = agent.id
    shell_skill_name = shell_skill.name

    shell_tool = _tool_def("runtime_authorized_shell_tool")
    registry = get_skill_registry()
    registry.register(
        skill_name=shell_skill_name,
        tool_defs=[shell_tool],
        executors={"runtime_authorized_shell_tool": _test_executor},
        runtime_spec={
            "name": shell_skill_name,
            "version": "1.0.0",
            "source_type": "local",
            "manifest_hash": "authorized-shell-runtime-hash",
            "permissions": ["shell"],
            "executor_kind": "python",
        },
    )

    try:
        run = await create_pipeline_run_for_session(db_session, session, "bug_fix")
        await db_session.commit()
        run_id = run.id

        fake_engine = FakeSkillEngine()
        runtime = StageRuntime(engine=fake_engine, session_factory=test_session_factory)

        chunks = []
        async for chunk in runtime.run_current_stage(
            task_id="task-high-risk-skill-auth-runtime",
            pipeline_run_id=run_id,
            user_id=user_id,
            user_message="需要执行一次测试命令",
            conversation_history=[],
            tools=[shell_tool],
            llm=object(),
            config=object(),
            sse_publish=lambda _event_type, _data: None,
            agent_name="CodeSoul",
            advanced_context={
                "intent": "bug_fix",
                "agent_profile_id": agent_id,
                "skill_authorization": {
                    "authorized_skill_names": [shell_skill_name],
                    "authorized_permissions": ["shell"],
                    "source": "user_confirmation",
                },
            },
        ):
            chunks.append(chunk)
    finally:
        registry.unregister(shell_skill_name)

    assert chunks == ["stage output"]
    assert fake_engine.kwargs is not None
    assert [tool["function"]["name"] for tool in fake_engine.kwargs["tools"]] == [
        "runtime_authorized_shell_tool"
    ]
    policy_context = fake_engine.kwargs["advanced_context"]["skill_policy"]
    assert policy_context["allowed_tool_count"] == 1
    assert policy_context["authorized_skill_names"] == [shell_skill_name]
    assert policy_context["authorized_permissions"] == ["shell"]
    assert policy_context["excluded_tools"] == []

    result = await db_session.execute(
        select(EvalEvent).where(
            EvalEvent.pipeline_run_id == run_id,
            EvalEvent.event_type == "skill_authorization_granted",
        )
    )
    [event] = result.scalars().all()
    assert event.status == "success"
    assert event.stage_id == "locate"
    assert event.skill_name == shell_skill_name
    assert event.tool_name == "runtime_authorized_shell_tool"
    assert event.metadata_json["permissions"] == ["shell"]
    assert event.metadata_json["source"] == "user_confirmation"


@pytest.mark.asyncio
async def test_stage_runtime_emits_skill_authorization_required_for_bound_high_risk_skill(
    db_session: AsyncSession,
    test_session_factory,
    fake_user: User,
):
    user_id = fake_user.id
    project = Project(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name="high-risk-skill-event-runtime-test",
        tech_tags=["FastAPI"],
        status="active",
    )
    session = Session(
        id=str(uuid.uuid4()),
        user_id=user_id,
        project_id=project.id,
        title="高风险 Skill 授权事件会话",
        intent_type="bug_fix",
    )
    agent = Agent(
        id=str(uuid.uuid4()),
        name=f"High Risk Event Agent {uuid.uuid4()}",
        capabilities=["testing"],
        model="claude-3-sonnet",
        status="active",
    )
    shell_skill = Skill(
        id=str(uuid.uuid4()),
        name=f"event-shell-skill-{uuid.uuid4().hex[:8]}",
        version="1.0.0",
        description="shell skill requiring runtime authorization",
        permissions=["shell"],
        runtime_spec={},
        enabled=True,
        source_type="local",
    )
    agent_skill = AgentSkill(agent_id=agent.id, skill_id=shell_skill.id, enabled=True)
    db_session.add_all([project, session, agent, shell_skill, agent_skill])
    await db_session.commit()
    agent_id = agent.id
    shell_skill_name = shell_skill.name

    shell_tool = _tool_def("runtime_event_shell_tool")
    registry = get_skill_registry()
    registry.register(
        skill_name=shell_skill_name,
        tool_defs=[shell_tool],
        executors={"runtime_event_shell_tool": _test_executor},
        runtime_spec={
            "name": shell_skill_name,
            "version": "1.0.0",
            "source_type": "local",
            "manifest_hash": "event-shell-runtime-hash",
            "permissions": ["shell"],
            "executor_kind": "python",
        },
    )

    events: list[tuple[str, dict]] = []

    async def capture_event(event_type: str, data: dict) -> None:
        events.append((event_type, data))

    try:
        run = await create_pipeline_run_for_session(db_session, session, "bug_fix")
        await db_session.commit()
        run_id = run.id

        fake_engine = FakeSkillEngine()
        runtime = StageRuntime(engine=fake_engine, session_factory=test_session_factory)

        chunks = []
        async for chunk in runtime.run_current_stage(
            task_id="task-high-risk-skill-event-runtime",
            pipeline_run_id=run_id,
            user_id=user_id,
            user_message="需要执行一次测试命令",
            conversation_history=[],
            tools=[shell_tool],
            llm=object(),
            config=object(),
            sse_publish=capture_event,
            agent_name="CodeSoul",
            advanced_context={"intent": "bug_fix", "agent_profile_id": agent_id},
        ):
            chunks.append(chunk)
    finally:
        registry.unregister(shell_skill_name)

    assert chunks == ["stage output"]
    assert fake_engine.kwargs is not None
    assert fake_engine.kwargs["tools"] == []
    [event] = [item for item in events if item[0] == "skill_authorization_required"]
    assert event[1]["pipeline_run_id"] == run_id
    assert event[1]["stage_id"] == "locate"
    assert event[1]["skills"] == [
        {
            "skill_name": shell_skill_name,
            "tool_name": "runtime_event_shell_tool",
            "permissions": ["shell"],
        }
    ]

    result = await db_session.execute(
        select(EvalEvent).where(
            EvalEvent.pipeline_run_id == run_id,
            EvalEvent.event_type == "skill_authorization_required",
        )
    )
    [eval_event] = result.scalars().all()
    assert eval_event.status == "blocked"
    assert eval_event.stage_id == "locate"
    assert eval_event.skill_name == shell_skill_name
    assert eval_event.tool_name == "runtime_event_shell_tool"
    assert eval_event.metadata_json == {
        "permissions": ["shell"],
        "policy_key": "default",
        "reason": "permission_denied",
    }


@pytest.mark.asyncio
async def test_stage_runtime_records_resolved_model_route_and_passes_config(
    db_session: AsyncSession,
    test_session_factory,
    fake_user: User,
):
    user_id = fake_user.id
    provider_key = f"anthropic-{uuid.uuid4().hex[:8]}"
    model_key = f"anthropic/claude-3-5-sonnet-{uuid.uuid4().hex[:8]}"
    route_key = f"runtime-{uuid.uuid4().hex[:8]}"
    project = Project(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name="model-runtime-test",
        tech_tags=["FastAPI"],
        status="active",
    )
    session = Session(
        id=str(uuid.uuid4()),
        user_id=user_id,
        project_id=project.id,
        title="模型路由运行时会话",
        intent_type="bug_fix",
    )
    provider = LLMProviderSetting(
        id=str(uuid.uuid4()),
        user_id=user_id,
        provider_key=provider_key,
        name="Anthropic",
        base_url="https://api.anthropic.com",
        status="active",
    )
    model = LLMModelSetting(
        id=str(uuid.uuid4()),
        user_id=user_id,
        provider_id=provider.id,
        model_key=model_key,
        name="Claude 3.5 Sonnet",
        capabilities=["text", "code"],
        context_window=200000,
        status="active",
    )
    credential = LLMCredential(
        id=str(uuid.uuid4()),
        user_id=user_id,
        provider_id=provider.id,
        name="runtime-key",
        encrypted_secret=encrypt_secret("sk-ant-runtime-secret"),
        secret_hint="sk-ant...cret",
        active=True,
    )
    route = LLMRoute(
        id=str(uuid.uuid4()),
        user_id=user_id,
        route_key=route_key,
        name="Default Runtime Route",
        provider_id=provider.id,
        model_id=model.id,
        credential_id=credential.id,
        temperature=0.15,
        max_tokens=4096,
        timeout_seconds=30,
        fallback_route_keys=[],
        active=True,
    )
    db_session.add_all([project, session, provider, model, credential, route])
    await db_session.commit()

    run = await create_pipeline_run_for_session(db_session, session, "bug_fix")
    await db_session.commit()
    run_id = run.id

    fake_engine = FakeSkillEngine()
    runtime = StageRuntime(engine=fake_engine, session_factory=test_session_factory)

    chunks = []
    async for chunk in runtime.run_current_stage(
        task_id="task-model-runtime",
        pipeline_run_id=run_id,
        user_id=user_id,
        user_message="分析错误",
        conversation_history=[],
        tools=[],
        llm=object(),
        config=object(),
        sse_publish=lambda _event_type, _data: None,
        agent_name="CodeSoul",
        advanced_context={"intent": "bug_fix", "model_route_key": route_key},
    ):
        chunks.append(chunk)

    assert chunks == ["stage output"]
    assert fake_engine.kwargs is not None
    resolved_config = fake_engine.kwargs["config"]
    assert resolved_config.model == model_key
    assert resolved_config.temperature == 0.15
    assert resolved_config.max_tokens == 4096
    assert resolved_config.api_key == "sk-ant-runtime-secret"
    assert fake_engine.kwargs["advanced_context"]["model_route"] == {
        "route_key": route_key,
        "name": "Default Runtime Route",
        "source": "database",
        "provider_key": provider_key,
        "model_name": model_key,
        "credential_id": credential.id,
        "credential_name": "runtime-key",
        "fallback_route_keys": [],
        "requested_route_key": route_key,
    }
    assert fake_engine.kwargs["advanced_context"]["evaluation_context"] == {
        "project_id": project.id,
        "pipeline_run_id": run_id,
        "stage_id": "locate",
        "stage_name": "问题定位",
    }

    db_session.expire_all()
    refreshed = await get_pipeline_run_for_user_or_404(db_session, run_id, user_id)
    stage_by_id = {stage.stage_id: stage for stage in refreshed.stages}
    assert stage_by_id["locate"].model_route_key == route_key
    assert stage_by_id["locate"].model_route_name == "Default Runtime Route"
    assert stage_by_id["locate"].model_name == model_key
    assert stage_by_id["locate"].model_route_source == "database"


@pytest.mark.asyncio
@pytest.mark.parametrize("expected_artifact_type", ["report", "architecture"])
async def test_stage_runtime_creates_catalog_artifact_type_for_completed_stage(
    db_session: AsyncSession,
    test_session_factory,
    fake_user: User,
    monkeypatch: pytest.MonkeyPatch,
    expected_artifact_type: str,
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

    original_definition = get_stage_definition("bug_fix", "locate")
    assert original_definition is not None
    if expected_artifact_type != original_definition.output_artifact_types[0]:
        monkeypatch.setattr(
            runtime_module,
            "get_stage_definition",
            lambda *_args: replace(
                original_definition,
                output_artifact_types=(expected_artifact_type,),
            ),
        )

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
    assert artifact.artifact_type == expected_artifact_type
    assert artifact.file_type == "markdown"
    assert artifact.name == "问题定位.md"
    assert artifact.content == "stage output"
    metadata = dict(artifact.metadata_json)
    runtime_metadata = metadata.pop("runtime")
    assert metadata == {
        "intent_type": "bug_fix",
        "stage_id": "locate",
        "stage_name": "问题定位",
        "stage_order": 0,
        "task_id": "task-artifact",
        "origin": "stage_runtime",
    }
    assert runtime_metadata["agent_profile"]["id"]
    assert runtime_metadata["agent_profile"]["name"]
    assert runtime_metadata["agent_profile"]["source"] in {
        "system_default",
        "stage_default",
        "project_default",
        "user_override",
    }
    assert runtime_metadata["model_route"]["route_key"]
    assert runtime_metadata["model_route"]["name"]
    assert runtime_metadata["model_route"]["source"]
    assert runtime_metadata["model_name"]
    assert runtime_metadata["skill_policy_key"] == "default"


@pytest.mark.asyncio
async def test_stage_runtime_blocks_waiting_confirmation_stage(
    db_session: AsyncSession,
    test_session_factory,
    fake_user: User,
):
    user_id = fake_user.id
    project = Project(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name="confirmation-runtime-test",
        tech_tags=["FastAPI"],
        status="active",
    )
    session = Session(
        id=str(uuid.uuid4()),
        user_id=user_id,
        project_id=project.id,
        title="确认节点会话",
        intent_type="new_feature",
    )
    db_session.add_all([project, session])
    await db_session.commit()

    run = await create_pipeline_run_for_session(db_session, session, "new_feature")
    run_id = run.id
    run.stages[0].status = "waiting_confirmation"
    run.status = "waiting_confirmation"
    run.current_stage_id = "analysis"
    await db_session.commit()

    fake_engine = FakeSkillEngine()
    runtime = StageRuntime(engine=fake_engine, session_factory=test_session_factory)

    chunks = []
    async for chunk in runtime.run_current_stage(
        task_id="task-confirmation-block",
        pipeline_run_id=run.id,
        user_id=user_id,
        user_message="继续执行",
        conversation_history=[],
        tools=[],
        llm=object(),
        config=object(),
        sse_publish=lambda _event_type, _data: None,
        agent_name="CodeSoul",
        advanced_context={"intent": "new_feature"},
    ):
        chunks.append(chunk)

    assert fake_engine.called is False
    assert chunks == ["当前阶段正在等待确认，请先确认或提出修改意见。"]

    db_session.expire_all()
    refreshed = await get_pipeline_run_for_user_or_404(db_session, run_id, user_id)
    stage_by_id = {stage.stage_id: stage for stage in refreshed.stages}
    assert refreshed.status == "waiting_confirmation"
    assert refreshed.current_stage_id == "analysis"
    assert stage_by_id["analysis"].status == "waiting_confirmation"
