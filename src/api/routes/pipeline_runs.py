"""PipelineRun and stage state routes."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.database import get_async_session
from agent_forge.models import User
from agent_forge.pipeline.service import (
    complete_stage,
    create_pipeline_run_for_session,
    fail_stage,
    get_pipeline_run_for_user_or_404,
    get_session_for_pipeline_or_404,
    pipeline_run_to_dict,
    restore_stage,
    skip_stage,
    start_stage,
)
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
