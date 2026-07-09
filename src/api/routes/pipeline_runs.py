"""PipelineRun and stage state routes."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.api.sse import emit_confirm_resolved
from agent_forge.database import get_async_session
from agent_forge.models import Artifact, AuditLog, PipelineRun, PipelineStageState, User
from agent_forge.pipeline.service import (
    complete_stage,
    create_pipeline_run_for_session,
    fail_stage,
    get_pipeline_run_for_user_or_404,
    get_session_for_pipeline_or_404,
    pipeline_run_to_dict,
    restore_stage,
    resolve_stage_confirmation,
    skip_stage,
    start_stage,
)
from agent_forge.tracing import get_trace_id
from middleware.auth import get_current_user

router = APIRouter()
session_router = APIRouter()

IntentType = Literal["new_feature", "iteration", "ui_adjust", "bug_fix"]


class PipelineRunCreateRequest(BaseModel):
    intent_type: IntentType | None = None
    stage_overrides: dict[str, bool] = Field(default_factory=dict)


class PipelineStageStateResponse(BaseModel):
    id: str
    pipeline_run_id: str
    stage_id: str
    stage_name: str
    order_index: int
    required: bool
    status: str
    skip_reason: str | None
    confirmation_required: bool
    confirmation_action: str | None
    confirmation_feedback: str | None
    confirmation_resolved_at: datetime | None
    agent_profile_id: str | None
    agent_profile_name: str | None
    agent_profile_source: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PipelineRunResponse(BaseModel):
    id: str
    project_id: str
    session_id: str
    intent_type: str
    status: str
    current_stage_id: str | None
    created_at: datetime
    updated_at: datetime
    stages: list[PipelineStageStateResponse]


class StageConfirmationRequest(BaseModel):
    action: Literal["approve", "revise", "cancel"]
    feedback: str | None = Field(default=None, max_length=2000)


@session_router.post(
    "/{session_id}/pipeline-runs",
    response_model=PipelineRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session_pipeline_run(
    session_id: str,
    body: PipelineRunCreateRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    session = await get_session_for_pipeline_or_404(db, session_id, current_user.id)
    run = await create_pipeline_run_for_session(
        db,
        session=session,
        intent_type=body.intent_type,
        stage_overrides=body.stage_overrides,
    )
    await db.commit()
    await db.refresh(run, attribute_names=["stages"])
    return pipeline_run_to_dict(run)


@router.get("/{run_id}", response_model=PipelineRunResponse)
async def get_pipeline_run(
    run_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    run = await get_pipeline_run_for_user_or_404(db, run_id, current_user.id)
    return pipeline_run_to_dict(run)


@router.post("/{run_id}/stages/{stage_id}/skip", response_model=PipelineRunResponse)
async def skip_pipeline_stage(
    run_id: str,
    stage_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    run = await get_pipeline_run_for_user_or_404(db, run_id, current_user.id)
    skip_stage(run, stage_id)
    await db.commit()
    await db.refresh(run, attribute_names=["stages"])
    return pipeline_run_to_dict(run)


@router.post("/{run_id}/stages/{stage_id}/restore", response_model=PipelineRunResponse)
async def restore_pipeline_stage(
    run_id: str,
    stage_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    run = await get_pipeline_run_for_user_or_404(db, run_id, current_user.id)
    restore_stage(run, stage_id)
    await db.commit()
    await db.refresh(run, attribute_names=["stages"])
    return pipeline_run_to_dict(run)


@router.post("/{run_id}/stages/{stage_id}/start", response_model=PipelineRunResponse)
async def start_pipeline_stage(
    run_id: str,
    stage_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    run = await get_pipeline_run_for_user_or_404(db, run_id, current_user.id)
    start_stage(run, stage_id)
    await db.commit()
    await db.refresh(run, attribute_names=["stages"])
    return pipeline_run_to_dict(run)


@router.post("/{run_id}/stages/{stage_id}/complete", response_model=PipelineRunResponse)
async def complete_pipeline_stage(
    run_id: str,
    stage_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    run = await get_pipeline_run_for_user_or_404(db, run_id, current_user.id)
    complete_stage(run, stage_id)
    await db.commit()
    await db.refresh(run, attribute_names=["stages"])
    return pipeline_run_to_dict(run)


@router.post("/{run_id}/stages/{stage_id}/confirm", response_model=PipelineRunResponse)
async def confirm_pipeline_stage(
    run_id: str,
    stage_id: str,
    body: StageConfirmationRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    run = await get_pipeline_run_for_user_or_404(db, run_id, current_user.id)
    stage = _stage_or_none(run, stage_id)
    resolve_stage_confirmation(run, stage_id, body.action, body.feedback)
    _add_confirmation_audit(db, current_user.id, run, stage_id, body)
    task_id = await _confirmation_task_id(db, stage)
    await db.commit()
    await db.refresh(run, attribute_names=["stages"])

    if task_id:
        await emit_confirm_resolved(
            task_id=task_id,
            project_id=run.project_id,
            session_id=run.session_id,
            pipeline_run_id=run.id,
            stage_id=stage_id,
            action=body.action,
        )

    return pipeline_run_to_dict(run)


@router.post("/{run_id}/stages/{stage_id}/fail", response_model=PipelineRunResponse)
async def fail_pipeline_stage(
    run_id: str,
    stage_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    run = await get_pipeline_run_for_user_or_404(db, run_id, current_user.id)
    fail_stage(run, stage_id)
    await db.commit()
    await db.refresh(run, attribute_names=["stages"])
    return pipeline_run_to_dict(run)


def _stage_or_none(run: PipelineRun, stage_id: str) -> PipelineStageState | None:
    return next((stage for stage in run.stages if stage.stage_id == stage_id), None)


def _add_confirmation_audit(
    db: AsyncSession,
    user_id: str,
    run: PipelineRun,
    stage_id: str,
    body: StageConfirmationRequest,
) -> None:
    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            action=f"pipeline.confirm.{body.action}",
            resource="pipeline_stage_state",
            user_id=user_id,
            trace_id=get_trace_id() or run.id,
            status="success",
            degraded=False,
            details={
                "pipeline_run_id": run.id,
                "project_id": run.project_id,
                "session_id": run.session_id,
                "stage_id": stage_id,
                "feedback": body.feedback,
            },
        )
    )


async def _confirmation_task_id(
    db: AsyncSession,
    stage: PipelineStageState | None,
) -> str | None:
    if not stage:
        return None
    result = await db.execute(
        select(Artifact)
        .where(Artifact.stage_state_id == stage.id)
        .order_by(Artifact.created_at.desc())
    )
    artifact = result.scalars().first()
    task_id = (artifact.metadata_json or {}).get("task_id") if artifact else None
    return task_id if isinstance(task_id, str) and task_id else None
