"""Pipeline state machine service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from agent_forge.models import PipelineRun, PipelineStageState
from agent_forge.models.session import Session
from agent_forge.pipeline.catalog import get_stage_definitions_for_intent, normalize_intent

TERMINAL_STAGE_STATUSES = {"completed", "skipped"}


def _now() -> datetime:
    return datetime.now(UTC)


def pipeline_run_to_dict(run: PipelineRun) -> dict:
    stages = sorted(run.stages, key=lambda stage: stage.order_index)
    return {
        "id": run.id,
        "project_id": run.project_id,
        "session_id": run.session_id,
        "intent_type": run.intent_type,
        "status": run.status,
        "current_stage_id": run.current_stage_id,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
        "stages": [
            {
                "id": stage.id,
                "pipeline_run_id": stage.pipeline_run_id,
                "stage_id": stage.stage_id,
                "stage_name": stage.stage_name,
                "order_index": stage.order_index,
                "required": stage.required,
                "status": stage.status,
                "skip_reason": stage.skip_reason,
                "confirmation_required": stage.confirmation_required,
                "confirmation_action": stage.confirmation_action,
                "confirmation_feedback": stage.confirmation_feedback,
                "confirmation_resolved_at": stage.confirmation_resolved_at,
                "agent_profile_id": stage.agent_profile_id,
                "agent_profile_name": stage.agent_profile_name,
                "agent_profile_source": stage.agent_profile_source,
                "model_route_key": stage.model_route_key,
                "model_route_name": stage.model_route_name,
                "model_name": stage.model_name,
                "model_route_source": stage.model_route_source,
                "started_at": stage.started_at,
                "completed_at": stage.completed_at,
                "created_at": stage.created_at,
                "updated_at": stage.updated_at,
            }
            for stage in stages
        ],
    }


async def create_pipeline_run_for_session(
    db: AsyncSession,
    session: Session,
    intent_type: str | None,
    stage_overrides: dict[str, bool] | None = None,
) -> PipelineRun:
    if not session.project_id:
        raise HTTPException(status_code=400, detail="Session must belong to a project")

    normalized_intent = normalize_intent(intent_type or session.intent_type)
    run = PipelineRun(
        id=str(uuid.uuid4()),
        project_id=session.project_id,
        session_id=session.id,
        intent_type=normalized_intent,
        status="planned",
    )
    db.add(run)

    stages: list[PipelineStageState] = []
    overrides = stage_overrides or {}
    for index, config in enumerate(get_stage_definitions_for_intent(normalized_intent)):
        skipped_by_user = overrides.get(config.stage_id) is False and not config.required
        stage = PipelineStageState(
            id=str(uuid.uuid4()),
            pipeline_run_id=run.id,
            stage_id=config.stage_id,
            stage_name=config.stage_name,
            order_index=index,
            required=config.required,
            status="skipped" if skipped_by_user else "pending",
            skip_reason="user_override" if skipped_by_user else None,
            confirmation_required=config.confirmation_required,
        )
        db.add(stage)
        stages.append(stage)

    run.stages = stages
    run.current_stage_id = _first_active_stage_id(stages)
    session.intent_type = normalized_intent
    session.current_pipeline_run_id = run.id
    await db.flush()
    return run


async def get_pipeline_run_for_user_or_404(
    db: AsyncSession,
    run_id: str,
    user_id: str,
) -> PipelineRun:
    result = await db.execute(
        select(PipelineRun)
        .join(Session, PipelineRun.session_id == Session.id)
        .where(PipelineRun.id == run_id, Session.user_id == user_id)
        .options(selectinload(PipelineRun.stages))
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="PipelineRun not found")
    return run


async def get_session_for_pipeline_or_404(
    db: AsyncSession,
    session_id: str,
    user_id: str,
) -> Session:
    result = await db.execute(
        select(Session).where(Session.id == session_id, Session.user_id == user_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def skip_stage(run: PipelineRun, stage_id: str, reason: str = "user_skipped") -> PipelineRun:
    stage = _stage_or_404(run, stage_id)
    if stage.required:
        raise HTTPException(status_code=400, detail="Required stage cannot be skipped")
    if stage.status in {"completed", "running"}:
        raise HTTPException(status_code=400, detail="Stage cannot be skipped from current status")

    stage.status = "skipped"
    stage.skip_reason = reason
    stage.completed_at = _now()
    _refresh_run_pointer(run)
    return run


def restore_stage(run: PipelineRun, stage_id: str) -> PipelineRun:
    stage = _stage_or_404(run, stage_id)
    if stage.required:
        raise HTTPException(status_code=400, detail="Required stage does not need restore")
    if stage.status != "skipped":
        return run

    stage.status = "pending"
    stage.skip_reason = None
    stage.completed_at = None
    _refresh_run_pointer(run)
    return run


def start_stage(run: PipelineRun, stage_id: str) -> PipelineRun:
    stage = _stage_or_404(run, stage_id)
    if stage.status != "pending":
        raise HTTPException(status_code=400, detail="Stage cannot be started from current status")

    stage.status = "running"
    stage.started_at = stage.started_at or _now()
    run.status = "running"
    run.current_stage_id = stage.stage_id
    return run


def complete_stage(run: PipelineRun, stage_id: str) -> PipelineRun:
    stage = _stage_or_404(run, stage_id)
    if stage.status not in {"running", "pending"}:
        raise HTTPException(status_code=400, detail="Stage cannot be completed from current status")

    if stage.confirmation_required and stage.status != "waiting_confirmation":
        stage.status = "waiting_confirmation"
        stage.completed_at = _now()
        if not stage.started_at:
            stage.started_at = stage.completed_at
        run.status = "waiting_confirmation"
        run.current_stage_id = stage.stage_id
        return run

    stage.status = "completed"
    stage.completed_at = _now()
    if not stage.started_at:
        stage.started_at = stage.completed_at
    _refresh_run_pointer(run)
    return run


def resolve_stage_confirmation(
    run: PipelineRun,
    stage_id: str,
    action: str,
    feedback: str | None = None,
) -> PipelineRun:
    stage = _stage_or_404(run, stage_id)
    if stage.status != "waiting_confirmation":
        raise HTTPException(status_code=400, detail="Stage is not waiting for confirmation")
    if action not in {"approve", "revise", "cancel"}:
        raise HTTPException(status_code=400, detail="Unsupported confirmation action")

    normalized_feedback = feedback.strip()[:2000] if feedback else None
    stage.confirmation_action = action
    stage.confirmation_feedback = normalized_feedback
    stage.confirmation_resolved_at = _now()

    if action == "approve":
        stage.status = "completed"
        _refresh_run_pointer(run)
        if run.current_stage_id is not None:
            run.status = "running"
        return run

    if action == "revise":
        stage.status = "pending"
        stage.started_at = None
        stage.completed_at = None
        run.status = "planned"
        run.current_stage_id = stage.stage_id
        return run

    stage.status = "failed"
    run.status = "cancelled"
    run.current_stage_id = stage.stage_id
    return run


def fail_stage(run: PipelineRun, stage_id: str) -> PipelineRun:
    stage = _stage_or_404(run, stage_id)
    if stage.status in TERMINAL_STAGE_STATUSES:
        raise HTTPException(status_code=400, detail="Terminal stage cannot be failed")
    stage.status = "failed"
    run.status = "failed"
    run.current_stage_id = stage.stage_id
    return run


def _stage_or_404(run: PipelineRun, stage_id: str) -> PipelineStageState:
    for stage in run.stages:
        if stage.stage_id == stage_id:
            return stage
    raise HTTPException(status_code=404, detail="Stage not found")


def _first_active_stage_id(stages: list[PipelineStageState]) -> str | None:
    for stage in sorted(stages, key=lambda item: item.order_index):
        if stage.status not in TERMINAL_STAGE_STATUSES:
            return stage.stage_id
    return None


def _refresh_run_pointer(run: PipelineRun) -> None:
    next_stage_id = _first_active_stage_id(run.stages)
    run.current_stage_id = next_stage_id
    if next_stage_id is None:
        run.status = "completed"
    elif run.status in {"planned", "completed", "waiting_confirmation"}:
        run.status = "planned"
