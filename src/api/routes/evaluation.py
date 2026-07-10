"""Evaluation feedback routes."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.database import get_async_session
from agent_forge.evaluation import EvaluationService
from agent_forge.models import User
from middleware.auth import get_current_user

router = APIRouter()


@router.get("/summary")
async def get_evaluation_summary(
    project_id: str | None = Query(default=None),
    pipeline_run_id: str | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    return await EvaluationService.get_summary(
        db,
        user_id=current_user.id,
        project_id=project_id,
        pipeline_run_id=pipeline_run_id,
        start_date=start_date,
        end_date=end_date,
    )
