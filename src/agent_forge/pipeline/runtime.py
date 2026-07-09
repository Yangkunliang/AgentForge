"""Runtime bridge between PipelineRun stage state and SkillExecutionEngine."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_forge.artifacts.service import create_stage_artifact
from agent_forge.api.sse import (
    emit_artifact_created,
    emit_confirm_required,
    emit_pipeline_started,
    emit_stage_completed,
    emit_stage_started,
)
from agent_forge.database import async_session_factory
from agent_forge.agents.resolver import AgentProfile, resolve_agent_profile
from agent_forge.models import PipelineRun, PipelineStageState
from agent_forge.pipeline.catalog import get_stage_definition, stage_definition_to_dict
from agent_forge.pipeline.service import (
    complete_stage,
    fail_stage,
    get_pipeline_run_for_user_or_404,
    start_stage,
)
from agent_forge.skills.dispatcher import SkillDispatcher
from agent_forge.skills.engine import SkillExecutionEngine

SsePublisher = Callable[[str, dict], Any]


class StageRuntime:
    """Advance the current PipelineRun stage around a SkillExecutionEngine run."""

    def __init__(
        self,
        engine: SkillExecutionEngine | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self.engine = engine or SkillExecutionEngine(SkillDispatcher())
        self.session_factory = session_factory or async_session_factory

    async def run_current_stage(
        self,
        *,
        task_id: str,
        pipeline_run_id: str | None,
        user_id: str | None,
        user_message: str,
        conversation_history: list[dict],
        tools: list[dict],
        llm: Any,
        config: Any,
        sse_publish: SsePublisher,
        agent_name: str,
        advanced_context: dict | None,
        source_message_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        active_stage_id: str | None = None
        confirmation_context: dict | None = None
        blocked_reason: str | None = None
        agent_profile: AgentProfile | None = None
        stage_output_chunks: list[str] = []
        if pipeline_run_id and user_id:
            active_stage_id, confirmation_context, blocked_reason, agent_profile = await self._start_current_stage(
                task_id=task_id,
                pipeline_run_id=pipeline_run_id,
                user_id=user_id,
                fallback_agent_name=agent_name,
                advanced_context=advanced_context,
            )

        if blocked_reason == "waiting_confirmation":
            yield "当前阶段正在等待确认，请先确认或提出修改意见。"
            return

        try:
            async_gen = await self.engine.run(
                user_message=user_message,
                conversation_history=conversation_history,
                tools=tools,
                llm=llm,
                config=config,
                sse_publish=sse_publish,
                user_id=user_id,
                agent_name=agent_profile.name if agent_profile else agent_name,
                advanced_context=_merge_runtime_context(advanced_context, confirmation_context, agent_profile),
            )

            async for chunk in async_gen:
                if chunk:
                    stage_output_chunks.append(chunk)
                yield chunk
        except Exception:
            if active_stage_id and pipeline_run_id and user_id:
                await self._fail_stage(pipeline_run_id, user_id, active_stage_id)
            raise
        else:
            if active_stage_id and pipeline_run_id and user_id:
                await self._complete_stage(
                    task_id=task_id,
                    pipeline_run_id=pipeline_run_id,
                    user_id=user_id,
                    stage_id=active_stage_id,
                    stage_output="".join(stage_output_chunks),
                    source_message_id=source_message_id,
                )

    async def _start_current_stage(
        self,
        *,
        task_id: str,
        pipeline_run_id: str,
        user_id: str,
        fallback_agent_name: str,
        advanced_context: dict | None,
    ) -> tuple[str | None, dict | None, str | None, AgentProfile | None]:
        async with self.session_factory() as db:
            run = await get_pipeline_run_for_user_or_404(db, pipeline_run_id, user_id)
            await emit_pipeline_started(
                task_id=task_id,
                project_id=run.project_id,
                session_id=run.session_id,
                pipeline_run_id=run.id,
                intent_type=run.intent_type,
            )

            stage_id = run.current_stage_id
            if not stage_id:
                return None, None, None, None

            stage = _find_stage(run, stage_id)
            if stage and stage.status == "waiting_confirmation":
                return None, None, "waiting_confirmation", None

            stage_definition = get_stage_definition(run.intent_type, stage_id)
            agent_profile = await resolve_agent_profile(
                db,
                stage_definition=stage_definition,
                user_override_agent_id=_agent_id_from_context(advanced_context, "agent_profile_id"),
                project_default_agent_id=_agent_id_from_context(advanced_context, "project_default_agent_id"),
                fallback_agent_name=fallback_agent_name,
            )
            confirmation_context = _confirmation_context(stage, stage_definition)
            if stage and stage.status == "pending":
                stage.agent_profile_id = agent_profile.id
                stage.agent_profile_name = agent_profile.name
                stage.agent_profile_source = agent_profile.source
                start_stage(run, stage_id)
                await db.commit()

            await emit_stage_started(
                task_id=task_id,
                project_id=run.project_id,
                session_id=run.session_id,
                pipeline_run_id=run.id,
                stage_id=stage_id,
            )
            return stage_id, confirmation_context, None, agent_profile

    async def _complete_stage(
        self,
        *,
        task_id: str,
        pipeline_run_id: str,
        user_id: str,
        stage_id: str,
        stage_output: str,
        source_message_id: str | None,
    ) -> None:
        async with self.session_factory() as db:
            run = await get_pipeline_run_for_user_or_404(db, pipeline_run_id, user_id)
            stage = _find_stage(run, stage_id)
            if not stage or stage.status in {"completed", "skipped", "failed"}:
                return

            complete_stage(run, stage_id)
            artifact = await create_stage_artifact(
                db,
                run=run,
                stage=stage,
                task_id=task_id,
                content=stage_output,
                source_message_id=source_message_id,
            )
            artifact_payload = {
                "project_id": artifact.project_id,
                "session_id": artifact.session_id,
                "pipeline_run_id": artifact.pipeline_run_id,
                "stage_id": stage.stage_id,
                "artifact_id": artifact.id,
                "artifact_type": artifact.artifact_type,
                "name": artifact.name,
            }
            requires_confirmation = stage.status == "waiting_confirmation"
            await db.commit()
            await emit_artifact_created(task_id=task_id, **artifact_payload)
            if requires_confirmation:
                await emit_confirm_required(
                    task_id=task_id,
                    project_id=run.project_id,
                    session_id=run.session_id,
                    pipeline_run_id=run.id,
                    stage_id=stage_id,
                    stage_name=stage.stage_name,
                    artifact_id=artifact.id,
                    artifact_name=artifact.name,
                )
            else:
                await emit_stage_completed(
                    task_id=task_id,
                    project_id=run.project_id,
                    session_id=run.session_id,
                    pipeline_run_id=run.id,
                    stage_id=stage_id,
                )

    async def _fail_stage(self, pipeline_run_id: str, user_id: str, stage_id: str) -> None:
        async with self.session_factory() as db:
            run = await get_pipeline_run_for_user_or_404(db, pipeline_run_id, user_id)
            stage = _find_stage(run, stage_id)
            if not stage or stage.status in {"completed", "skipped", "failed"}:
                return

            fail_stage(run, stage_id)
            await db.commit()


def _find_stage(run: PipelineRun, stage_id: str) -> PipelineStageState | None:
    return next((stage for stage in run.stages if stage.stage_id == stage_id), None)


def _confirmation_context(stage: PipelineStageState | None, stage_definition: Any | None = None) -> dict | None:
    if not stage or not stage.confirmation_feedback:
        return None
    context = {
        "stage_id": stage.stage_id,
        "stage_name": stage.stage_name,
        "feedback": stage.confirmation_feedback,
        "action": stage.confirmation_action,
    }
    if stage_definition:
        context["stage_definition"] = stage_definition_to_dict(stage_definition, stage.order_index)
    return context


def _merge_confirmation_context(base: dict | None, confirmation: dict | None) -> dict | None:
    if not confirmation:
        return base
    merged = dict(base or {})
    merged["confirmation_feedback"] = confirmation
    return merged


def _merge_runtime_context(
    base: dict | None,
    confirmation: dict | None,
    agent_profile: AgentProfile | None,
) -> dict | None:
    merged = _merge_confirmation_context(base, confirmation)
    if not agent_profile:
        return merged
    runtime_context = dict(merged or {})
    runtime_context["agent_profile"] = agent_profile.to_context()
    return runtime_context


def _agent_id_from_context(context: dict | None, key: str) -> str | None:
    if not context:
        return None
    value = context.get(key)
    return value if isinstance(value, str) and value else None
