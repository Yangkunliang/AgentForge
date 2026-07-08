"""Runtime bridge between PipelineRun stage state and SkillExecutionEngine."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_forge.artifacts.service import create_stage_artifact
from agent_forge.api.sse import (
    emit_artifact_created,
    emit_pipeline_started,
    emit_stage_completed,
    emit_stage_started,
)
from agent_forge.database import async_session_factory
from agent_forge.models import PipelineRun, PipelineStageState
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
        stage_output_chunks: list[str] = []
        if pipeline_run_id and user_id:
            active_stage_id = await self._start_current_stage(
                task_id=task_id,
                pipeline_run_id=pipeline_run_id,
                user_id=user_id,
            )

        try:
            async_gen = await self.engine.run(
                user_message=user_message,
                conversation_history=conversation_history,
                tools=tools,
                llm=llm,
                config=config,
                sse_publish=sse_publish,
                user_id=user_id,
                agent_name=agent_name,
                advanced_context=advanced_context,
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
    ) -> str | None:
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
                return None

            stage = _find_stage(run, stage_id)
            if stage and stage.status in {"pending", "waiting_confirmation"}:
                start_stage(run, stage_id)
                await db.commit()

            await emit_stage_started(
                task_id=task_id,
                project_id=run.project_id,
                session_id=run.session_id,
                pipeline_run_id=run.id,
                stage_id=stage_id,
            )
            return stage_id

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
            await db.commit()
            await emit_stage_completed(
                task_id=task_id,
                project_id=run.project_id,
                session_id=run.session_id,
                pipeline_run_id=run.id,
                stage_id=stage_id,
            )
            await emit_artifact_created(task_id=task_id, **artifact_payload)

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
