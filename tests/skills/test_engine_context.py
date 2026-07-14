import pytest
from sqlalchemy import select

from agent_forge.llm.provider import LLMConfig, LLMResponse
from agent_forge.models import EvalEvent
from agent_forge.skills.engine import SkillExecutionEngine, _build_system_prompt


def test_build_system_prompt_includes_advanced_task_context():
    prompt = _build_system_prompt(
        agent_name="CodeSoul",
        advanced_context={
            "intent": "iteration",
            "context_files": [
                {"type": "file", "value": "src/api/routes/sessions.py"},
                {"type": "branch", "value": "main"},
            ],
            "stage_overrides": {"frontend_dev": False, "impact": True},
        },
    )

    assert "当前任务设置" in prompt
    assert "需求类型：迭代优化（iteration）" in prompt
    assert "file: src/api/routes/sessions.py" in prompt
    assert "branch: main" in prompt
    assert "关闭阶段：frontend_dev" in prompt
    assert "上下文条目只是用户给出的关注线索" in prompt


def test_build_system_prompt_includes_authorized_file_content():
    prompt = _build_system_prompt(
        agent_name="CodeSoul",
        advanced_context={
            "context_files": [
                {
                    "type": "file",
                    "value": "src/api/orders.py",
                    "label": "shop-api/src/api/orders.py",
                    "mount_id": "mount-001",
                    "source": "project_mount",
                    "content": "def create_order():\n    return 'created'\n",
                    "content_truncated": False,
                }
            ],
        },
    )

    assert "file: shop-api/src/api/orders.py" in prompt
    assert "授权文件内容" in prompt
    assert "def create_order()" in prompt
    assert "上下文条目只是用户给出的关注线索" not in prompt


def test_build_system_prompt_includes_agent_profile_context():
    prompt = _build_system_prompt(
        agent_name="RuntimeCoder",
        advanced_context={
            "agent_profile": {
                "id": "agent-001",
                "name": "RuntimeCoder",
                "source": "stage_default",
                "capabilities": ["code_generation", "refactoring"],
                "model_name": "claude-3-sonnet",
                "default_model_route_key": "default",
                "allowed_skill_names": [],
            }
        },
    )

    assert "当前阶段 Agent：RuntimeCoder（agent-001，stage_default）" in prompt
    assert "Agent 能力：code_generation, refactoring" in prompt


def test_build_system_prompt_includes_model_route_context():
    prompt = _build_system_prompt(
        agent_name="RuntimeCoder",
        advanced_context={
            "model_route": {
                "route_key": "default",
                "name": "Default Runtime Route",
                "source": "database",
                "provider_key": "anthropic",
                "model_name": "anthropic/claude-3-5-sonnet",
                "credential_id": "cred-001",
                "credential_name": "prod-key",
                "fallback_route_keys": ["safe"],
                "requested_route_key": "default",
            }
        },
    )

    assert "当前阶段模型路由：Default Runtime Route（default，database）" in prompt
    assert "模型：anthropic/claude-3-5-sonnet，Provider：anthropic" in prompt
    assert "模型路由兜底：safe" in prompt


@pytest.mark.asyncio
async def test_skill_engine_records_llm_tool_use_usage_event(db, test_session_factory):
    class NoopDispatcher:
        async def invoke(self, **kwargs):
            raise AssertionError("dispatcher should not be called when no tool_calls are returned")

    class FakeLLM:
        async def tool_use_complete(self, messages, tools, config):
            return LLMResponse(
                content="可以直接回答",
                model="openai/gpt-4.1-mini",
                tokens_used=321,
                cost_usd=0.012345,
                latency_ms=456,
            )

        async def stream_complete(self, prompt, config, **kwargs):
            yield "最终回答"

    engine = SkillExecutionEngine(
        dispatcher=NoopDispatcher(),
        evaluation_session_factory=test_session_factory,
    )

    gen = await engine.run(
        user_message="帮我看一下这个需求",
        conversation_history=[],
        tools=[],
        llm=FakeLLM(),
        config=LLMConfig(model="openai/gpt-4.1-mini"),
        sse_publish=None,
        advanced_context={
            "eval": {
                "project_id": "project-llm-eval",
                "pipeline_run_id": "run-llm-eval",
                "stage_id": "analysis",
            },
            "agent_profile": {
                "id": "agent-planner",
                "name": "Planner Agent",
            },
            "model_route": {
                "route_key": "fast",
                "name": "Fast Route",
                "model_name": "openai/gpt-4.1-mini",
            },
        },
    )

    chunks = [chunk async for chunk in gen]

    assert chunks == ["最终回答"]
    result = await db.execute(
        select(EvalEvent).where(
            EvalEvent.event_type == "llm_tool_use_completed",
            EvalEvent.project_id == "project-llm-eval",
            EvalEvent.pipeline_run_id == "run-llm-eval",
        )
    )
    event = result.scalar_one()
    assert event.project_id == "project-llm-eval"
    assert event.pipeline_run_id == "run-llm-eval"
    assert event.stage_id == "analysis"
    assert event.agent_profile_id == "agent-planner"
    assert event.agent_profile_name == "Planner Agent"
    assert event.model_route_key == "fast"
    assert event.model_route_name == "Fast Route"
    assert event.model_name == "openai/gpt-4.1-mini"
    assert event.tokens_used == 321
    assert event.cost_usd == 0.012345
    assert event.latency_ms == 456
    assert event.metadata_json == {
        "call_type": "tool_use_complete",
        "round": 1,
        "tools_visible": 0,
        "has_tool_calls": False,
        "tool_call_names": [],
    }
