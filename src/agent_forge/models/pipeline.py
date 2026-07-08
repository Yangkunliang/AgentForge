"""Pipeline run and stage state models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .project import Project
    from .session import Session


class PipelineRun(Base, TimestampMixin):
    """一次需求按 intent 生成的阶段化执行计划。"""

    __tablename__ = "pipeline_runs"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    intent_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="planned", index=True)
    current_stage_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    project: Mapped[Project] = relationship("Project", back_populates="pipeline_runs")
    session: Mapped[Session] = relationship("Session", back_populates="pipeline_runs")
    stages: Mapped[list[PipelineStageState]] = relationship(
        back_populates="pipeline_run",
        cascade="all, delete-orphan",
        order_by="PipelineStageState.order_index",
    )

    def __repr__(self) -> str:
        return f"<PipelineRun id={self.id} intent={self.intent_type} status={self.status}>"


class PipelineStageState(Base, TimestampMixin):
    """PipelineRun 内单个阶段的运行状态。"""

    __tablename__ = "pipeline_stage_states"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    pipeline_run_id: Mapped[str] = mapped_column(
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    stage_name: Mapped[str] = mapped_column(String(120), nullable=False)
    order_index: Mapped[int] = mapped_column(nullable=False)
    required: Mapped[bool] = mapped_column(nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", index=True)
    skip_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    confirmation_required: Mapped[bool] = mapped_column(nullable=False, default=False)
    confirmation_action: Mapped[str | None] = mapped_column(String(30), nullable=True)
    confirmation_feedback: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    confirmation_resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    pipeline_run: Mapped[PipelineRun] = relationship("PipelineRun", back_populates="stages")

    def __repr__(self) -> str:
        return f"<PipelineStageState id={self.id} stage={self.stage_id} status={self.status}>"
