"""Task Pydantic Schemas"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SubTaskItem(BaseModel):
    id: str
    description: str
    status: str
    assigned_agent_id: str | None = None
    result: str | None = None

    class Config:
        from_attributes = True


class TaskCreateRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=2000)
    priority: str = Field(default="medium", pattern=r"^(low|medium|high)$")
    expected_models: list[str] = Field(default_factory=list)


class TaskListItem(BaseModel):
    id: str
    description: str
    status: str
    priority: str
    trace_id: str
    created_at: datetime
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    total: int
    page: int
    per_page: int
    items: list[TaskListItem]


class TaskDetailResponse(BaseModel):
    id: str
    description: str
    status: str
    priority: str
    result: str | None = None
    trace_id: str
    created_at: datetime
    completed_at: datetime | None = None
    sub_tasks: list[SubTaskItem] = []

    class Config:
        from_attributes = True


class TaskFeedbackRequest(BaseModel):
    thumbs: int = Field(..., ge=-1, le=1)
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=500)


class TaskFeedbackResponse(BaseModel):
    message: str
